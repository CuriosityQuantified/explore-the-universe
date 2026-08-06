"""Cross-match Celery task: query all 4 catalogs in parallel per object.

Seventh step in the 9-task pipeline chain:
  download_fits -> validate_wcs -> generate_tiles -> detect_sources
  -> segment_sam -> generate_cutouts -> cross_match_catalogs
  -> classify_objects -> detect_anomalies

Receives the output dict from generate_cutouts.  For each AstronomicalObject
in the observation, computes an adaptive search radius from its bounding box
and the WCS pixel scale, then queries SIMBAD, NED, SDSS, and Gaia in parallel
using a ThreadPoolExecutor.

ALL matches from ALL catalogs are stored as CatalogCrossMatch records (no
deduplication).  AstronomicalObject indexed fields are updated using the
best-priority catalog that returned a match (SIMBAD > NED > SDSS > Gaia).
If a catalog API fails after 3 retries the sentinel {'status': 'not_queried'}
is returned by the client; that catalog is skipped for this observation and
the task continues — it does NOT abort.
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from sqlalchemy import func as sql_func

from api.db.session import SessionLocal
from pipeline.catalog_clients import (
    compute_search_radius_arcsec,
    gaia_client,
    ned_client,
    sdss_client,
    simbad_client,
)
from pipeline.celery_app import celery_app
from shared.config import settings
from shared.models import (
    AstronomicalObject,
    CatalogCrossMatch,
    Observation,
    PipelineStatus,
    ProcessingStep,
    StepStatus,
)
from shared.s3 import get_s3_client

logger = logging.getLogger(__name__)

# Ordered priority list for updating AstronomicalObject indexed fields.
_CATALOG_PRIORITY = ("simbad", "ned", "sdss", "gaia")

# JWST NIRCam long-wavelength channel pixel scale — used as a safe default
# when FITS WCS cannot be recovered.
_DEFAULT_PIXEL_SCALE_ARCSEC = 0.063


# ---------------------------------------------------------------------------
# Pixel-scale helper
# ---------------------------------------------------------------------------


def _get_pixel_scale(
    session, observation_uuid: uuid.UUID, observation_uuid_hex: str
) -> float:
    """Return WCS pixel scale in arcsec/px for this observation.

    Recovers FITS S3 keys from the download_fits ProcessingStep metadata,
    downloads the first FITS file, and derives the pixel scale from the WCS.
    Falls back to _DEFAULT_PIXEL_SCALE_ARCSEC on any failure.
    """
    download_step = (
        session.query(ProcessingStep)
        .filter(
            ProcessingStep.observation_uuid == observation_uuid,
            ProcessingStep.step_name == "download_fits",
        )
        .first()
    )
    fits_s3_keys: list[str] = []
    if download_step and download_step.step_output_metadata:
        fits_s3_keys = download_step.step_output_metadata.get("fits_s3_keys", [])

    if not fits_s3_keys:
        logger.warning(
            "No FITS S3 keys for observation %s — using default pixel scale %.4f arcsec/px",
            observation_uuid_hex,
            _DEFAULT_PIXEL_SCALE_ARCSEC,
        )
        return _DEFAULT_PIXEL_SCALE_ARCSEC

    s3 = get_s3_client()
    fd, temp_path = tempfile.mkstemp(suffix=".fits")
    os.close(fd)
    try:
        s3.download_file(settings.s3_bucket_fits_raw, fits_s3_keys[0], temp_path)
        with fits.open(temp_path) as hdul:
            header = None
            for hdu in hdul:
                if hdu.data is not None and hdu.header.get("NAXIS", 0) >= 2:
                    header = hdu.header
                    break
            if header is None:
                header = hdul[0].header
            wcs = WCS(header)
            # pixel_scale_matrix returns deg/px; determinant gives area → sqrt = linear scale
            scale_deg = float(np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix))))
            return scale_deg * 3600.0
    except Exception as exc:
        logger.warning(
            "Could not derive pixel scale for observation %s: %s — using default",
            observation_uuid_hex,
            exc,
        )
        return _DEFAULT_PIXEL_SCALE_ARCSEC
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ---------------------------------------------------------------------------
# Per-catalog query (runs inside ThreadPoolExecutor)
# ---------------------------------------------------------------------------


def _query_one_catalog(
    name: str, fn, coord: SkyCoord, radius_arcsec: float
) -> tuple[str, list[dict]]:
    return name, fn(coord, radius_arcsec=radius_arcsec)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, acks_late=True)
def cross_match_catalogs(self, cutout_result: dict) -> dict:
    """Cross-match detected objects against SIMBAD, NED, SDSS, and Gaia.

    Seventh step in the 9-task pipeline chain.
    Receives the output dict from generate_cutouts.
    """
    observation_uuid_hex = cutout_result["observation_uuid"]
    observation_uuid = uuid.UUID(observation_uuid_hex)

    database_session = SessionLocal()
    processing_step: Optional[ProcessingStep] = None

    try:
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="cross_match_catalogs",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        logger.info("Starting cross-match for observation %s", observation_uuid_hex)

        all_objects = (
            database_session.query(AstronomicalObject)
            .filter(AstronomicalObject.source_observation_uuid == observation_uuid)
            .all()
        )

        if not all_objects:
            processing_step.step_status = StepStatus.completed
            processing_step.step_completed_at = sql_func.now()
            processing_step.step_output_metadata = {
                "objects_processed": 0,
                "total_matches": 0,
                "catalogs_queried": [],
                "catalogs_failed": [],
            }
            database_session.commit()
            return {
                "observation_uuid": observation_uuid_hex,
                "objects_processed": 0,
                "total_matches": 0,
                "catalogs_queried": [],
                "status": "completed",
            }

        pixel_scale_arcsec = _get_pixel_scale(
            database_session, observation_uuid, observation_uuid_hex
        )
        logger.info(
            "Pixel scale for observation %s: %.4f arcsec/px",
            observation_uuid_hex,
            pixel_scale_arcsec,
        )

        catalog_fns = {
            "simbad": simbad_client.query_simbad_region,
            "ned": ned_client.query_ned_region,
            "sdss": sdss_client.query_sdss_region,
            "gaia": gaia_client.query_gaia_region,
        }

        total_matches = 0
        catalogs_failed: set[str] = set()

        for batch_start in range(0, len(all_objects), 50):
            batch = all_objects[batch_start : batch_start + 50]

            for obj in batch:
                coord = SkyCoord(
                    ra=obj.sky_coordinate_ra_degrees,
                    dec=obj.sky_coordinate_dec_degrees,
                    unit="deg",
                    frame="icrs",
                )
                radius_arcsec = compute_search_radius_arcsec(
                    bounding_box_pixels=obj.bounding_box_pixels or {
                        "xmin": 0, "xmax": 5, "ymin": 0, "ymax": 5
                    },
                    pixel_scale_arcsec_per_pixel=pixel_scale_arcsec,
                    compact_source_radius_arcsec=settings.classification_compact_source_radius_arcsec,
                    extended_source_scale_factor=settings.classification_extended_source_scale_factor,
                    compact_source_threshold_arcsec=settings.classification_compact_source_threshold_arcsec,
                )

                # Query all 4 catalogs in parallel
                catalog_results: dict[str, list[dict]] = {}
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {
                        executor.submit(
                            _query_one_catalog, name, fn, coord, radius_arcsec
                        ): name
                        for name, fn in catalog_fns.items()
                    }
                    for future in as_completed(futures):
                        cat_name, results = future.result()
                        catalog_results[cat_name] = results

                # Accumulate matches per catalog for priority-based field update
                obj_matches: dict[str, list[dict]] = {
                    n: [] for n in _CATALOG_PRIORITY
                }

                for cat_name, results in catalog_results.items():
                    for match in results:
                        if match.get("status") == "not_queried":
                            catalogs_failed.add(cat_name)
                            logger.warning(
                                "Catalog %s not queried for object %s: %s",
                                cat_name,
                                obj.object_uuid,
                                match.get("error", "unknown error"),
                            )
                            continue

                        sep = float(match.get("angular_separation_arcsec") or 0.0)
                        prob = 1.0 / (1.0 + sep)
                        record = CatalogCrossMatch(
                            object_uuid=obj.object_uuid,
                            catalog_name=cat_name,
                            catalog_source_id=str(
                                match.get("catalog_source_id") or ""
                            ),
                            angular_separation_arcseconds=sep,
                            match_probability_score=prob,
                            raw_catalog_response=match,
                        )
                        database_session.add(record)
                        obj_matches[cat_name].append(match)
                        total_matches += 1

                # Update AstronomicalObject indexed fields with best-priority match.
                # Iterate SIMBAD → NED → SDSS → Gaia; only fill fields not yet set.
                for cat_name in _CATALOG_PRIORITY:
                    matches = obj_matches[cat_name]
                    if not matches:
                        continue
                    best = matches[0]

                    if not obj.catalog_object_name:
                        obj.catalog_object_name = best.get("catalog_source_id")
                    if not obj.classified_object_type:
                        obj.classified_object_type = best.get("object_type")
                    if not obj.classification_source_catalog:
                        obj.classification_source_catalog = cat_name

                    # Magnitude: SIMBAD flux(V), SDSS petroMag_r, Gaia phot_g_mean_mag
                    if obj.catalog_magnitude is None and cat_name in ("simbad", "sdss", "gaia"):
                        mag = best.get("magnitude")
                        if mag is not None:
                            obj.catalog_magnitude = float(mag)

                    # Redshift: SIMBAD, NED, SDSS (Gaia has none)
                    if obj.catalog_redshift is None and cat_name in ("simbad", "ned", "sdss"):
                        z = best.get("redshift")
                        if z is not None:
                            obj.catalog_redshift = float(z)

            database_session.flush()

        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = {
            "objects_processed": len(all_objects),
            "total_matches": total_matches,
            "catalogs_queried": list(set(_CATALOG_PRIORITY) - catalogs_failed),
            "catalogs_failed": list(catalogs_failed),
        }
        database_session.commit()

        logger.info(
            "Cross-match complete for observation %s: %d objects, %d total matches, "
            "failed catalogs: %s",
            observation_uuid_hex,
            len(all_objects),
            total_matches,
            catalogs_failed or "none",
        )

        return {
            "observation_uuid": observation_uuid_hex,
            "objects_processed": len(all_objects),
            "total_matches": total_matches,
            "catalogs_queried": list(set(_CATALOG_PRIORITY) - catalogs_failed),
            "status": "completed",
        }

    except Exception:
        logger.exception(
            "cross_match_catalogs failed for observation %s", observation_uuid_hex
        )
        try:
            if processing_step:
                processing_step.step_status = StepStatus.failed
                processing_step.step_completed_at = sql_func.now()
                database_session.commit()
        except Exception:
            database_session.rollback()
        try:
            obs = (
                database_session.query(Observation)
                .filter(Observation.observation_uuid == observation_uuid)
                .first()
            )
            if obs:
                obs.pipeline_status = PipelineStatus.failed
                database_session.commit()
        except Exception:
            database_session.rollback()
        raise

    finally:
        database_session.close()
