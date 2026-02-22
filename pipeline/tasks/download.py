"""MAST download Celery task for JWST observations.

Queries the Mikulski Archive for Space Telescopes (MAST) for JWST observations,
downloads calibrated FITS files, uploads them to MinIO, and records provenance
metadata in PostgreSQL. This is the first step in the pipeline chain.

Usage:
    download_fits.delay(observation_uuid_hex, archive_observation_id)
"""

import logging
import os
import shutil
import uuid
from pathlib import Path

from astroquery.mast import Observations
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


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def download_fits(
    self,
    observation_uuid_hex: str,
    archive_observation_id: str,
    archive_program_id: str | None = None,
) -> dict:
    """Download calibrated FITS files from MAST and upload to MinIO.

    Receives a pre-created observation UUID from the orchestrator (Plan 03).
    Queries MAST for matching JWST observations, filters to calibrated FITS
    products, downloads them, uploads to MinIO fits-raw bucket, and records
    provenance metadata.

    Args:
        observation_uuid_hex: Hex string of the pre-created observation UUID.
        archive_observation_id: MAST observation ID (e.g., 'jw02736-o001_t001_nircam_clear-f444w').
        archive_program_id: Optional JWST program ID (e.g., '2736').

    Returns:
        Dict with observation_uuid, list of fits_s3_keys, and product_count.
    """
    observation_uuid = uuid.UUID(observation_uuid_hex)
    database_session = SessionLocal()

    # Create a unique subdirectory for this download to avoid collisions
    download_directory = Path(settings.mast_download_directory) / observation_uuid_hex
    download_directory.mkdir(parents=True, exist_ok=True)

    processing_step = None

    try:
        # --- Step a: Create ProcessingStep record ---
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="download",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        logger.info(
            "Starting MAST download for observation %s (archive_id=%s, program=%s)",
            observation_uuid_hex,
            archive_observation_id,
            archive_program_id,
        )

        # --- Step b: Query MAST for JWST observations ---
        # CRITICAL: Use query_criteria() first, then pass table to get_product_list().
        # Do NOT pass raw obs_id strings to get_product_list -- that causes
        # the obsid vs obs_id confusion pitfall.
        query_criteria = {
            "obs_collection": "JWST",
            "obs_id": archive_observation_id,
            "dataRights": "PUBLIC",
        }
        if archive_program_id is not None:
            query_criteria["proposal_id"] = archive_program_id

        observation_table = Observations.query_criteria(**query_criteria)

        if len(observation_table) == 0:
            raise ValueError(
                f"No MAST observations found for obs_id='{archive_observation_id}', "
                f"program_id='{archive_program_id}'"
            )

        logger.info(
            "MAST query returned %d observation(s) for %s",
            len(observation_table),
            archive_observation_id,
        )

        # --- Step c: Get product list from query results ---
        product_list = Observations.get_product_list(observation_table)

        if len(product_list) == 0:
            raise ValueError(
                f"No products found for observation '{archive_observation_id}'"
            )

        # --- Step d: Filter to calibrated FITS science products ---
        filtered_products = Observations.filter_products(
            product_list,
            extension="fits",
            calib_level=[2, 3],
            productType="SCIENCE",
        )

        if len(filtered_products) == 0:
            raise ValueError(
                f"No calibrated FITS science products found for "
                f"observation '{archive_observation_id}' "
                f"(total products before filter: {len(product_list)})"
            )

        logger.info(
            "Filtered to %d calibrated FITS science products (from %d total)",
            len(filtered_products),
            len(product_list),
        )

        # --- Step e: Download filtered products to local temp directory ---
        download_manifest = Observations.download_products(
            filtered_products,
            download_dir=str(download_directory),
        )

        downloaded_file_paths = [
            Path(row["Local Path"])
            for row in download_manifest
            if row["Status"] == "COMPLETE"
        ]

        if len(downloaded_file_paths) == 0:
            raise RuntimeError(
                f"All MAST downloads failed for observation '{archive_observation_id}'. "
                f"Manifest statuses: {[row['Status'] for row in download_manifest]}"
            )

        logger.info(
            "Downloaded %d files to %s",
            len(downloaded_file_paths),
            download_directory,
        )

        # --- Step f: Upload each FITS file to MinIO ---
        s3_client = get_s3_client()
        fits_s3_keys = []
        upload_manifest_entries = []

        for file_path in downloaded_file_paths:
            s3_key = f"{observation_uuid_hex}/{file_path.name}"
            file_size_bytes = file_path.stat().st_size

            s3_client.upload_file(
                str(file_path),
                settings.s3_bucket_fits_raw,
                s3_key,
            )

            fits_s3_keys.append(s3_key)
            upload_manifest_entries.append({
                "s3_key": s3_key,
                "file_size_bytes": file_size_bytes,
                "original_filename": file_path.name,
            })

            logger.info(
                "Uploaded %s to s3://%s/%s (%d bytes)",
                file_path.name,
                settings.s3_bucket_fits_raw,
                s3_key,
                file_size_bytes,
            )

        # --- Step g: Extract provenance metadata from MAST query results ---
        # Use the first observation row for metadata (all rows share the same observation)
        first_observation_row = observation_table[0]

        telescope_name = str(
            first_observation_row.get("obs_collection", "JWST")
        )
        instrument_name = str(
            first_observation_row.get("instrument_name", "unknown")
        )
        spectral_filters_raw = str(
            first_observation_row.get("filters", "")
        )
        spectral_filters = (
            [f.strip() for f in spectral_filters_raw.split(";")]
            if spectral_filters_raw
            else []
        )
        total_exposure_seconds = float(
            first_observation_row.get("t_exptime", 0.0)
        )

        # --- Step h: Update the Observation record with provenance fields ---
        observation_record = (
            database_session.query(Observation)
            .filter(Observation.observation_uuid == observation_uuid)
            .first()
        )

        if observation_record is not None:
            observation_record.telescope_name = telescope_name
            observation_record.instrument_name = instrument_name
            observation_record.spectral_filters = spectral_filters
            observation_record.total_exposure_seconds = total_exposure_seconds
            observation_record.pipeline_status = PipelineStatus.downloading
            database_session.commit()
        else:
            logger.warning(
                "Observation record %s not found in database -- "
                "provenance metadata not persisted",
                observation_uuid_hex,
            )

        # --- Step i: Update ProcessingStep to completed ---
        step_output_metadata = {
            "fits_s3_keys": fits_s3_keys,
            "product_count": len(fits_s3_keys),
            "upload_manifest": upload_manifest_entries,
            "mast_query_criteria": query_criteria,
            "mast_observation_count": len(observation_table),
            "mast_total_products": len(product_list),
            "mast_filtered_products": len(filtered_products),
            "provenance": {
                "telescope_name": telescope_name,
                "instrument_name": instrument_name,
                "spectral_filters": spectral_filters,
                "total_exposure_seconds": total_exposure_seconds,
            },
        }

        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = step_output_metadata
        database_session.commit()

        logger.info(
            "Download task completed for observation %s: %d FITS files uploaded",
            observation_uuid_hex,
            len(fits_s3_keys),
        )

        # --- Step k: Clean up local download directory ---
        shutil.rmtree(download_directory, ignore_errors=True)

        # --- Step l: Return result ---
        return {
            "observation_uuid": observation_uuid_hex,
            "fits_s3_keys": fits_s3_keys,
            "product_count": len(fits_s3_keys),
        }

    except Exception as exception:
        logger.exception(
            "Download task failed for observation %s: %s",
            observation_uuid_hex,
            exception,
        )

        # --- Step j: Mark processing step and observation as failed ---
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

        # Clean up local files on failure too
        shutil.rmtree(download_directory, ignore_errors=True)

        raise

    finally:
        database_session.close()
