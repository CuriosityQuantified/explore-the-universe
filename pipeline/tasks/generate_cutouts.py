"""Cutout generation Celery task (sixth step in the 9-task pipeline chain).

Extracts per-object cutout images from the original FITS data using bounding
boxes with 10% padding. For each detected astronomical object, generates three
files:
  - cutout_stretched.png: auto-stretched (ZScale + asinh) display version
  - cutout_raw.png: raw linear (percentile-clipped) version
  - cutout.fits: FITS file with preserved WCS headers

All cutout files are uploaded to the MinIO segmentation bucket under
{observation_uuid}/{object_uuid}/.

Sixth step in the 9-task pipeline chain:
  download_fits -> validate_wcs -> generate_tiles -> detect_sources
  -> segment_sam -> generate_cutouts -> cross_match_catalogs
  -> classify_objects -> detect_anomalies

PipelineStatus.completed is set by detect_anomalies (the final task),
not by this task.

Usage:
    # Called as part of Celery chain (receives segment_sam output dict)
    generate_cutouts({"observation_uuid": "...", "object_uuids": [...], ...})
"""

import logging
import os
import shutil
import tempfile
import uuid

import numpy as np
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.visualization import AsinhStretch, ZScaleInterval
from astropy.wcs import WCS
from PIL import Image
from sqlalchemy import func as sql_func

from api.db.session import SessionLocal
from pipeline.celery_app import celery_app
from shared.config import settings
from shared.models import (
    AstronomicalObject,
    Observation,
    PipelineStatus,
    ProcessingStep,
    StepStatus,
)
from shared.s3 import get_s3_client

logger = logging.getLogger(__name__)

# Flush DB updates in batches of this size to avoid accumulating too many
# pending changes in the SQLAlchemy session.
DB_FLUSH_BATCH_SIZE = 100


def _find_sci_extension(hdul):
    """Find the SCI extension in a FITS HDU list.

    Same logic as detect_sources._find_sci_extension. Copied here to avoid
    circular dependency between task modules.

    Args:
        hdul: An opened astropy FITS HDU list.

    Returns:
        The HDU containing science image data.

    Raises:
        ValueError: If no HDU with image data can be found.
    """
    try:
        sci_hdu = hdul["SCI"]
        if sci_hdu.header.get("NAXIS", 0) > 0:
            return sci_hdu
    except KeyError:
        pass

    primary_hdu = hdul[0]
    if primary_hdu.header.get("NAXIS", 0) > 0:
        logger.warning(
            "Using primary HDU (hdul[0]) instead of named SCI extension"
        )
        return primary_hdu

    for index, hdu in enumerate(hdul):
        if hdu.header.get("NAXIS", 0) > 0:
            logger.warning(
                "Using extension %d (%s) as fallback", index, hdu.name
            )
            return hdu

    raise ValueError("No HDU with image data (NAXIS > 0) found in FITS file")


def _extract_cutout_data(
    fits_data,
    wcs_object,
    centroid_x,
    centroid_y,
    bbox,
    padding_fraction=0.1,
):
    """Extract a WCS-preserving cutout from FITS data using Cutout2D.

    Computes a padded bounding box from the object's bounding box pixels,
    centered on the centroid, and extracts the cutout with astropy's Cutout2D.
    Edge objects that extend beyond the image boundary get zero-filled pixels
    via mode='partial'.

    Args:
        fits_data: 2D float32 numpy array of the full FITS image.
        wcs_object: Astropy WCS for the image.
        centroid_x: X pixel coordinate of the object centroid (global coords).
        centroid_y: Y pixel coordinate of the object centroid (global coords).
        bbox: Dict with xmin, xmax, ymin, ymax in pixel coordinates.
        padding_fraction: Fraction of bounding box size to add as padding
            on each side. Default 0.1 (10%).

    Returns:
        Cutout2D object with .data (2D array) and .wcs attributes.
    """
    bbox_width = bbox["xmax"] - bbox["xmin"]
    bbox_height = bbox["ymax"] - bbox["ymin"]

    padded_width = int(bbox_width * (1 + 2 * padding_fraction))
    padded_height = int(bbox_height * (1 + 2 * padding_fraction))

    # Minimum size 16px in each dimension to avoid degenerate cutouts
    padded_width = max(padded_width, 16)
    padded_height = max(padded_height, 16)

    cutout = Cutout2D(
        fits_data,
        position=(centroid_x, centroid_y),
        size=(padded_height, padded_width),
        wcs=wcs_object,
        mode="partial",
        fill_value=0.0,
    )

    return cutout


def _create_stretched_png(cutout_data, output_path):
    """Create auto-stretched PNG using asinh stretch (same as tile.py).

    Applies ZScale interval computation on the cutout data, linear rescaling,
    asinh stretch, and conversion to uint8 for PNG output.

    Args:
        cutout_data: 2D float32 numpy array from Cutout2D.data.
        output_path: File path to save the PNG.
    """
    data = np.nan_to_num(cutout_data, nan=0.0, posinf=0.0, neginf=0.0)

    # Compute ZScale limits on the cutout itself
    interval = ZScaleInterval()
    vmin, vmax = interval.get_limits(data)

    # Linear rescale to [0, 1]
    if vmax > vmin:
        normalized = np.clip((data - vmin) / (vmax - vmin), 0, 1)
    else:
        normalized = np.zeros_like(data)

    # Asinh stretch
    stretch = AsinhStretch(a=0.1)
    stretched = stretch(normalized)

    # Convert to uint8
    uint8_data = (stretched * 255).astype(np.uint8)

    Image.fromarray(uint8_data, mode="L").save(output_path)


def _create_raw_png(cutout_data, output_path):
    """Create raw linear PNG (no stretch, percentile-clipped linear mapping).

    Maps the cutout data to [0, 255] using 1st/99th percentile clipping
    for a simple linear representation without any non-linear stretch.

    Args:
        cutout_data: 2D float32 numpy array from Cutout2D.data.
        output_path: File path to save the PNG.
    """
    data = np.nan_to_num(cutout_data, nan=0.0, posinf=0.0, neginf=0.0)

    # Percentile clipping for linear mapping
    vmin = np.nanpercentile(data, 1)
    vmax = np.nanpercentile(data, 99)

    if vmax > vmin:
        data_clipped = np.clip(data, vmin, vmax)
        uint8_data = ((data_clipped - vmin) / (vmax - vmin) * 255).astype(
            np.uint8
        )
    else:
        uint8_data = np.zeros_like(data, dtype=np.uint8)

    Image.fromarray(uint8_data, mode="L").save(output_path)


def _create_fits_cutout(cutout_2d, output_path):
    """Create a FITS file with the cutout data and preserved WCS.

    Writes a minimal FITS file containing only the cutout data and the
    WCS header from the Cutout2D object.

    Args:
        cutout_2d: Cutout2D object with .data and .wcs attributes.
        output_path: File path to save the FITS file.
    """
    hdu = fits.PrimaryHDU(data=cutout_2d.data, header=cutout_2d.wcs.to_header())
    hdu.writeto(output_path, overwrite=True)


def _upload_cutout_files(
    s3_client, observation_uuid_hex, object_uuid_hex, temp_dir
):
    """Upload all cutout files for one object to MinIO segmentation bucket.

    Uploads cutout_stretched.png, cutout_raw.png, and cutout.fits from the
    temp directory to the segmentation bucket under the S3 key prefix
    {observation_uuid}/{object_uuid}/.

    Args:
        s3_client: boto3 S3 client instance.
        observation_uuid_hex: Observation UUID as hex string.
        object_uuid_hex: Object UUID as hex string.
        temp_dir: Directory containing the cutout files.

    Returns:
        Tuple of (s3_prefix, total_bytes_uploaded) where s3_prefix is the
        S3 key prefix string.
    """
    s3_prefix = f"{observation_uuid_hex}/{object_uuid_hex}/"
    bucket = settings.s3_bucket_segmentation
    total_bytes = 0

    files_to_upload = [
        ("cutout_stretched.png", "image/png"),
        ("cutout_raw.png", "image/png"),
        ("cutout.fits", "application/fits"),
    ]

    for filename, content_type in files_to_upload:
        local_path = os.path.join(temp_dir, filename)
        if not os.path.exists(local_path):
            continue

        s3_key = f"{s3_prefix}{filename}"
        file_size = os.path.getsize(local_path)

        s3_client.upload_file(
            local_path,
            bucket,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )

        total_bytes += file_size

    return s3_prefix, total_bytes


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def generate_cutouts(self, segmentation_result: dict) -> dict:
    """Generate per-object cutout images (sixth pipeline step).

    Extracts per-object cutouts (dual PNG + FITS with WCS) from the original
    FITS data, uploads them to MinIO, and updates AstronomicalObject.cutout_s3_prefix.
    PipelineStatus.completed is set by detect_anomalies (the final task).

    Data flow:
        segmentation_result["observation_uuid"] -> observation UUID
        segmentation_result["fits_s3_keys"] -> FITS download for image data
        segmentation_result["object_uuids"] -> objects to generate cutouts for

    Args:
        segmentation_result: Dict from segment_sam containing at minimum
            observation_uuid. Also uses fits_s3_keys and object_uuids.

    Returns:
        Dict with observation_uuid, cutouts_generated count, and status.
    """
    observation_uuid_hex = segmentation_result["observation_uuid"]
    observation_uuid = uuid.UUID(observation_uuid_hex)
    fits_s3_keys = segmentation_result.get("fits_s3_keys", [])
    masks_generated = segmentation_result.get("masks_generated", 0)

    database_session = SessionLocal()
    processing_step = None
    temp_dir = None
    temp_fits_path = None

    try:
        # Create ProcessingStep record
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="generate_cutouts",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        logger.info(
            "Starting cutout generation for observation %s",
            observation_uuid_hex,
        )

        # If fits_s3_keys not in segmentation_result, recover from download
        # step metadata (same pattern as detect_sources)
        if not fits_s3_keys:
            download_step = (
                database_session.query(ProcessingStep)
                .filter(
                    ProcessingStep.observation_uuid == observation_uuid,
                    ProcessingStep.step_name == "download_fits",
                )
                .first()
            )
            if download_step and download_step.step_output_metadata:
                fits_s3_keys = download_step.step_output_metadata.get(
                    "fits_s3_keys", []
                )
            if not fits_s3_keys:
                raise ValueError(
                    f"No fits_s3_keys available for observation "
                    f"{observation_uuid_hex}"
                )

        # Query all AstronomicalObject records for this observation
        all_objects = (
            database_session.query(AstronomicalObject)
            .filter(
                AstronomicalObject.source_observation_uuid == observation_uuid
            )
            .all()
        )

        # Early exit if no objects
        if len(all_objects) == 0:
            processing_step.step_status = StepStatus.completed
            processing_step.step_completed_at = sql_func.now()
            processing_step.step_output_metadata = {"cutouts_generated": 0}

            database_session.commit()

            logger.info(
                "No objects to generate cutouts for observation %s "
                "-- pipeline completed",
                observation_uuid_hex,
            )

            return {
                "observation_uuid": observation_uuid_hex,
                "cutouts_generated": 0,
                "status": "completed",
            }

        # Download first FITS file from MinIO
        s3_client = get_s3_client()
        temp_fd, temp_fits_path = tempfile.mkstemp(suffix=".fits")
        os.close(temp_fd)

        s3_client.download_file(
            settings.s3_bucket_fits_raw,
            fits_s3_keys[0],
            temp_fits_path,
        )

        # Open FITS and get 2D data + WCS
        with fits.open(temp_fits_path, memmap=True, mode="denywrite") as hdul:
            sci_hdu = _find_sci_extension(hdul)
            fits_data = sci_hdu.data

            # Handle 3D+ FITS cubes: take first 2D slice
            if fits_data.ndim > 2:
                logger.info(
                    "FITS data has %d dimensions (shape=%s), "
                    "selecting first 2D slice",
                    fits_data.ndim,
                    fits_data.shape,
                )
                while fits_data.ndim > 2:
                    fits_data = fits_data[0]

            # Get WCS, use celestial sub-WCS for 3D+
            full_wcs = WCS(sci_hdu.header)
            if full_wcs.naxis > 2:
                wcs_object = full_wcs.celestial
            else:
                wcs_object = full_wcs

            # Fix byte order and cast to float32 (same as detect_sources)
            fits_data = np.array(fits_data, dtype=np.float32)

        # Process cutouts
        cutouts_generated = 0
        total_bytes_uploaded = 0
        temp_dir = tempfile.mkdtemp(prefix="cutouts_")

        for object_index, astro_object in enumerate(all_objects):
            pixel_x = astro_object.pixel_centroid_x
            pixel_y = astro_object.pixel_centroid_y
            bbox = astro_object.bounding_box_pixels

            if pixel_x is None or pixel_y is None or not bbox:
                logger.debug(
                    "Skipping object %s: missing centroid or bbox",
                    astro_object.object_uuid,
                )
                continue

            object_uuid_hex = astro_object.object_uuid.hex

            try:
                # Extract cutout with padding
                cutout = _extract_cutout_data(
                    fits_data,
                    wcs_object,
                    pixel_x,
                    pixel_y,
                    bbox,
                    padding_fraction=settings.segmentation_cutout_padding_fraction,
                )

                # Create cutout files in temp dir
                stretched_path = os.path.join(
                    temp_dir, "cutout_stretched.png"
                )
                raw_path = os.path.join(temp_dir, "cutout_raw.png")
                fits_path = os.path.join(temp_dir, "cutout.fits")

                _create_stretched_png(cutout.data, stretched_path)
                _create_raw_png(cutout.data, raw_path)
                _create_fits_cutout(cutout, fits_path)

                # Upload to MinIO
                s3_prefix, bytes_uploaded = _upload_cutout_files(
                    s3_client,
                    observation_uuid_hex,
                    object_uuid_hex,
                    temp_dir,
                )

                # Update DB record
                astro_object.cutout_s3_prefix = s3_prefix
                cutouts_generated += 1
                total_bytes_uploaded += bytes_uploaded

            except Exception as cutout_error:
                logger.warning(
                    "Failed to generate cutout for object %s: %s",
                    astro_object.object_uuid,
                    cutout_error,
                )
                continue

            finally:
                # Clean up temp files for this object (don't accumulate)
                for temp_file in [
                    "cutout_stretched.png",
                    "cutout_raw.png",
                    "cutout.fits",
                ]:
                    file_path = os.path.join(temp_dir, temp_file)
                    try:
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                    except OSError:
                        pass

            # Batch DB flush every DB_FLUSH_BATCH_SIZE objects
            if (object_index + 1) % DB_FLUSH_BATCH_SIZE == 0:
                database_session.flush()
                logger.debug(
                    "Flushed DB updates after %d objects", object_index + 1
                )

        # Update ProcessingStep to completed
        step_output_metadata = {
            "cutouts_generated": cutouts_generated,
            "total_bytes_uploaded": total_bytes_uploaded,
            "stretched_png_count": cutouts_generated,
            "raw_png_count": cutouts_generated,
            "fits_cutout_count": cutouts_generated,
        }
        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = step_output_metadata

        database_session.commit()

        logger.info(
            "Cutout generation completed for observation %s: %d cutouts, "
            "%.1f MB uploaded. Passing to cross_match_catalogs.",
            observation_uuid_hex,
            cutouts_generated,
            total_bytes_uploaded / (1024 * 1024) if total_bytes_uploaded else 0,
        )

        return {
            "observation_uuid": observation_uuid_hex,
            "cutouts_generated": cutouts_generated,
            "status": "completed",
        }

    except Exception as exception:
        logger.exception(
            "Cutout generation failed for observation %s: %s",
            observation_uuid_hex,
            exception,
        )

        # Mark processing step as failed
        if processing_step is not None:
            try:
                processing_step.step_status = StepStatus.failed
                processing_step.step_completed_at = sql_func.now()
                processing_step.error_message_text = str(exception)
                database_session.commit()
            except Exception:
                database_session.rollback()
                logger.exception(
                    "Failed to update ProcessingStep to failed status"
                )

        # Mark observation as failed
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
            logger.exception(
                "Failed to update Observation to failed status"
            )

        raise

    finally:
        # Clean up all temp files
        if temp_dir is not None and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if temp_fits_path is not None:
            try:
                os.unlink(temp_fits_path)
            except OSError:
                pass

        database_session.close()
