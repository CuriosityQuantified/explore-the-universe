"""WCS validation Celery task for FITS observations.

Extracts World Coordinate System (WCS) information from FITS SCI extension
headers, validates via pixel-to-world round-trip test, updates the Observation
record with pointing RA/Dec, and records provenance metadata from FITS headers.

This is the second step in the pipeline chain, receiving output from
download_fits and passing results to generate_tiles.

Usage:
    # Called as part of Celery chain (receives download_fits output dict)
    validate_wcs({"observation_uuid": "...", "fits_s3_keys": [...], "product_count": N})
"""

import logging
import os
import tempfile
import uuid

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from sqlalchemy import func as sql_func

from api.db.session import SessionLocal
from pipeline.celery_app import celery_app
from shared.config import settings
from shared.models import (
    Observation,
    PipelineStatus,
    ProcessingStep,
    StepStatus,
)
from shared.s3 import get_s3_client

logger = logging.getLogger(__name__)


def _find_sci_extension(hdul):
    """Find the SCI extension in a FITS HDU list.

    Checks for a named 'SCI' extension first (standard for JWST MEF files),
    then falls back to the primary HDU if no named SCI extension exists.
    Verifies the chosen HDU has actual image data (NAXIS > 0).

    Args:
        hdul: An opened astropy FITS HDU list.

    Returns:
        The HDU containing science image data.

    Raises:
        ValueError: If no HDU with image data can be found.
    """
    # Check for named SCI extension first (JWST MEF standard)
    try:
        sci_hdu = hdul["SCI"]
        if sci_hdu.header.get("NAXIS", 0) > 0:
            logger.info("Found named SCI extension with NAXIS=%d", sci_hdu.header["NAXIS"])
            return sci_hdu
        logger.warning("Named SCI extension found but has NAXIS=0, trying primary HDU")
    except KeyError:
        logger.info("No named SCI extension found, trying primary HDU")

    # Fall back to primary HDU
    primary_hdu = hdul[0]
    if primary_hdu.header.get("NAXIS", 0) > 0:
        logger.warning(
            "Using primary HDU (hdul[0]) instead of named SCI extension -- "
            "this FITS file may not follow JWST MEF convention"
        )
        return primary_hdu

    # Last resort: search all extensions for one with image data
    for index, hdu in enumerate(hdul):
        if hdu.header.get("NAXIS", 0) > 0:
            logger.warning(
                "Using extension %d (%s) as fallback -- no SCI or primary with image data",
                index,
                hdu.name,
            )
            return hdu

    raise ValueError("No HDU with image data (NAXIS > 0) found in FITS file")


def _validate_wcs_round_trip(wcs_object, nx, ny):
    """Validate WCS accuracy via pixel-to-world-to-pixel round-trip test.

    Tests corners and center of the image. Returns the maximum error in pixels
    and whether the WCS passes the 1.0 pixel threshold.

    Args:
        wcs_object: An astropy WCS instance.
        nx: Image width in pixels.
        ny: Image height in pixels.

    Returns:
        Tuple of (is_valid: bool, max_error_pixels: float).
    """
    test_pixels = np.array([
        [0, 0],
        [nx // 2, ny // 2],
        [nx - 1, ny - 1],
        [0, ny - 1],
        [nx - 1, 0],
    ], dtype=np.float64)

    try:
        world_coordinates = wcs_object.all_pix2world(test_pixels, 0)
        roundtrip_pixels = wcs_object.all_world2pix(world_coordinates, 0)
        max_error_pixels = float(np.max(np.abs(test_pixels - roundtrip_pixels)))

        is_valid = max_error_pixels < 1.0

        if not is_valid:
            logger.warning(
                "WCS round-trip validation failed: max_error=%.4f pixels (threshold=1.0)",
                max_error_pixels,
            )
        else:
            logger.info(
                "WCS round-trip validation passed: max_error=%.6f pixels",
                max_error_pixels,
            )

        return is_valid, max_error_pixels

    except Exception as wcs_error:
        logger.warning(
            "WCS round-trip validation could not be completed: %s", wcs_error
        )
        return False, float("inf")


def _extract_fits_header_provenance(header):
    """Extract provenance metadata from FITS header fields.

    Supplements MAST metadata extracted in Plan 01 with fields read directly
    from the FITS header (more authoritative for WCS-related fields).

    Args:
        header: An astropy FITS header.

    Returns:
        Dict of provenance fields extracted from the header.
    """
    provenance = {}

    # Telescope name
    telescope_name = header.get("TELESCOP")
    if telescope_name is not None:
        provenance["telescope_name"] = str(telescope_name).strip()

    # Instrument name
    instrument_name = header.get("INSTRUME")
    if instrument_name is not None:
        provenance["instrument_name"] = str(instrument_name).strip()

    # Spectral filters -- JWST uses FILTER, some instruments use FILTER1/FILTER2
    filter_value = header.get("FILTER")
    if filter_value is not None:
        provenance["spectral_filters"] = [str(filter_value).strip()]
    else:
        filter1 = header.get("FILTER1")
        if filter1 is not None:
            filters = [str(filter1).strip()]
            filter2 = header.get("FILTER2")
            if filter2 is not None:
                filters.append(str(filter2).strip())
            provenance["spectral_filters"] = filters

    # Exposure time
    exposure_time = header.get("EXPTIME")
    if exposure_time is not None:
        try:
            provenance["total_exposure_seconds"] = float(exposure_time)
        except (ValueError, TypeError):
            logger.warning("Could not parse EXPTIME value: %s", exposure_time)

    return provenance


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def validate_wcs(self, download_result: dict) -> dict:
    """Extract and validate WCS from FITS headers, update Observation with pointing.

    Receives the output dict from download_fits, downloads each FITS file from
    MinIO, extracts WCS from the SCI extension, validates via round-trip test,
    extracts provenance from FITS headers, and updates the Observation record
    with pointing RA/Dec coordinates.

    Args:
        download_result: Dict from download_fits containing:
            - observation_uuid: hex string of observation UUID
            - fits_s3_keys: list of S3 keys for FITS files in fits-raw bucket
            - product_count: number of FITS files

    Returns:
        Dict with observation_uuid, fits_s3_keys, wcs_valid flag,
        and image_dimensions for downstream tile generation.
    """
    observation_uuid_hex = download_result["observation_uuid"]
    fits_s3_keys = download_result["fits_s3_keys"]
    observation_uuid = uuid.UUID(observation_uuid_hex)

    database_session = SessionLocal()
    processing_step = None
    temp_files_to_clean = []

    try:
        # --- Step a: Create ProcessingStep record ---
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="validate_wcs",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        logger.info(
            "Starting WCS validation for observation %s (%d FITS files)",
            observation_uuid_hex,
            len(fits_s3_keys),
        )

        s3_client = get_s3_client()

        # Track results across all FITS files
        primary_center_ra_degrees = None
        primary_center_dec_degrees = None
        primary_image_dimensions = None
        overall_wcs_valid = True
        overall_max_error = 0.0
        all_header_provenance = {}

        # --- Step b: Process each FITS file ---
        for fits_index, fits_s3_key in enumerate(fits_s3_keys):
            logger.info(
                "Processing FITS file %d/%d: %s",
                fits_index + 1,
                len(fits_s3_keys),
                fits_s3_key,
            )

            # Download FITS from MinIO to local temp file
            temp_fd, temp_fits_path = tempfile.mkstemp(suffix=".fits")
            os.close(temp_fd)
            temp_files_to_clean.append(temp_fits_path)

            s3_client.download_file(
                settings.s3_bucket_fits_raw,
                fits_s3_key,
                temp_fits_path,
            )

            # Open FITS with memory mapping for efficiency
            with fits.open(temp_fits_path, memmap=True, mode="denywrite") as hdul:
                # Find the SCI extension
                sci_hdu = _find_sci_extension(hdul)
                header = sci_hdu.header

                # Get image dimensions
                ny = header.get("NAXIS2", 0)
                nx = header.get("NAXIS1", 0)

                if nx == 0 or ny == 0:
                    logger.warning(
                        "FITS file %s has zero-dimension image: nx=%d, ny=%d",
                        fits_s3_key, nx, ny,
                    )
                    continue

                # Extract WCS
                wcs_object = WCS(header)

                # Validate WCS with round-trip test
                is_valid, max_error_pixels = _validate_wcs_round_trip(
                    wcs_object, nx, ny
                )

                if not is_valid:
                    overall_wcs_valid = False
                overall_max_error = max(overall_max_error, max_error_pixels)

                # Extract pointing coordinates (image center)
                center_sky = wcs_object.pixel_to_world(nx // 2, ny // 2)
                center_ra_degrees = float(center_sky.ra.deg)
                center_dec_degrees = float(center_sky.dec.deg)

                logger.info(
                    "FITS %s: center RA=%.6f, Dec=%.6f, dimensions=%dx%d",
                    fits_s3_key,
                    center_ra_degrees,
                    center_dec_degrees,
                    nx,
                    ny,
                )

                # Use the first/primary FITS file for Observation pointing
                if fits_index == 0:
                    primary_center_ra_degrees = center_ra_degrees
                    primary_center_dec_degrees = center_dec_degrees
                    primary_image_dimensions = {"ny": ny, "nx": nx}

                # Extract provenance from FITS headers
                header_provenance = _extract_fits_header_provenance(header)
                if header_provenance:
                    all_header_provenance.update(header_provenance)

        # --- Step c: Update the Observation record with pointing ---
        if primary_center_ra_degrees is not None:
            observation_record = (
                database_session.query(Observation)
                .filter(Observation.observation_uuid == observation_uuid)
                .first()
            )

            if observation_record is not None:
                observation_record.pointing_ra_degrees = primary_center_ra_degrees
                observation_record.pointing_dec_degrees = primary_center_dec_degrees
                # pipeline_status remains as-is (still processing)
                database_session.commit()

                logger.info(
                    "Updated observation %s pointing: RA=%.6f, Dec=%.6f",
                    observation_uuid_hex,
                    primary_center_ra_degrees,
                    primary_center_dec_degrees,
                )
            else:
                logger.warning(
                    "Observation record %s not found in database -- "
                    "pointing coordinates not persisted",
                    observation_uuid_hex,
                )

        # --- Step d: Update ProcessingStep to completed ---
        step_output_metadata = {
            "wcs_valid": overall_wcs_valid,
            "max_round_trip_error_pixels": overall_max_error
            if overall_max_error != float("inf")
            else None,
            "center_ra_degrees": primary_center_ra_degrees,
            "center_dec_degrees": primary_center_dec_degrees,
            "image_dimensions": (
                [primary_image_dimensions["ny"], primary_image_dimensions["nx"]]
                if primary_image_dimensions is not None
                else None
            ),
            "fits_header_provenance": all_header_provenance,
            "files_processed": len(fits_s3_keys),
        }

        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = step_output_metadata
        database_session.commit()

        logger.info(
            "WCS validation completed for observation %s: wcs_valid=%s, max_error=%.6f",
            observation_uuid_hex,
            overall_wcs_valid,
            overall_max_error if overall_max_error != float("inf") else -1.0,
        )

        # --- Step g: Return result for downstream tile generation ---
        return {
            "observation_uuid": observation_uuid_hex,
            "fits_s3_keys": fits_s3_keys,
            "wcs_valid": overall_wcs_valid,
            "image_dimensions": primary_image_dimensions,
        }

    except Exception as exception:
        logger.exception(
            "WCS validation failed for observation %s: %s",
            observation_uuid_hex,
            exception,
        )

        # --- Step e: Mark processing step and observation as failed ---
        if processing_step is not None:
            try:
                processing_step.step_status = StepStatus.failed
                processing_step.step_completed_at = sql_func.now()
                processing_step.error_message_text = str(exception)
                database_session.commit()
            except Exception:
                database_session.rollback()
                logger.exception("Failed to update ProcessingStep to failed status")

        try:
            observation_record = (
                database_session.query(Observation)
                .filter(Observation.observation_uuid == observation_uuid)
                .first()
            )
            if observation_record is not None:
                observation_record.pipeline_status = PipelineStatus.failed
                database_session.commit()
        except Exception:
            database_session.rollback()
            logger.exception("Failed to update Observation to failed status")

        raise

    finally:
        # --- Step f: Clean up local temp files ---
        for temp_path in temp_files_to_clean:
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Failed to clean up temp file: %s", temp_path)

        database_session.close()
