"""DZI tile pyramid generation Celery task for FITS observations.

Converts FITS science data to normalized 8-bit images using ZScale + asinh
stretch, then generates Deep Zoom Image (DZI) tile pyramids via pyvips for
efficient multi-resolution viewing. Tiles are uploaded to MinIO for the
sky viewer (Phase 3) to consume.

Memory safety: FITS data is processed in row-band chunks (never loaded fully
into memory), and normalization parameters are computed once from a subsample
to ensure consistent stretch across all chunks (no visible seams).

This is the third step in the pipeline chain, receiving output from
validate_wcs. After tile generation, the pipeline continues to segmentation
tasks (detect_sources -> segment_sam -> generate_cutouts). This task does NOT
set the observation pipeline_status to completed — that is done by the final
task in the chain.

Usage:
    # Called as part of Celery chain (receives validate_wcs output dict)
    generate_tiles({"observation_uuid": "...", "fits_s3_keys": [...], ...})
"""

import logging
import os
import shutil
import tempfile
import uuid

import numpy as np
from astropy.io import fits
from astropy.visualization import AsinhStretch, ZScaleInterval
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

# Lazy import for pyvips -- the C library (libvips) may not be on the default
# search path on macOS (Homebrew installs to /opt/homebrew/lib).  Deferring
# the import to first use lets the module be loaded (and the Celery task
# registered) even when libvips is absent, e.g. during FastAPI startup or CI.
_pyvips = None


def _get_pyvips():
    """Lazily import pyvips, setting DYLD_LIBRARY_PATH for macOS Homebrew."""
    global _pyvips
    if _pyvips is None:
        import platform

        if platform.system() == "Darwin":
            dyld_path = os.environ.get("DYLD_LIBRARY_PATH", "")
            homebrew_lib = "/opt/homebrew/lib"
            if homebrew_lib not in dyld_path:
                os.environ["DYLD_LIBRARY_PATH"] = (
                    f"{homebrew_lib}:{dyld_path}" if dyld_path else homebrew_lib
                )
        import pyvips

        _pyvips = pyvips
    return _pyvips


# Number of rows per processing chunk. Balances memory usage vs overhead.
# 4096 rows at 16-bit, 16k pixels wide = ~128MB per chunk.
CHUNK_ROWS = 4096

# For images larger than this threshold (rows), use incremental strip joining
# instead of accumulating all strips in a list. This prevents memory issues
# with trillion-pixel images.
LARGE_IMAGE_ROW_THRESHOLD = 50_000


def _find_sci_extension(hdul):
    """Find the SCI extension in a FITS HDU list.

    Same logic as validate_wcs._find_sci_extension -- checks for named 'SCI'
    extension first (JWST MEF standard), falls back to primary HDU.

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


def _compute_normalization_parameters(fits_data, ny, nx):
    """Compute ZScale normalization parameters from a subsample of the image.

    Samples approximately 100 evenly-spaced rows from the FITS data to compute
    ZScale limits without loading the full image. These parameters are then
    applied consistently to all chunks during normalization.

    CRITICAL: Parameters are computed ONCE here and reused for all chunks.
    Per-chunk normalization would cause visible seams at tile boundaries.

    Args:
        fits_data: Memory-mapped FITS data array (ny, nx).
        ny: Image height in pixels.
        nx: Image width in pixels.

    Returns:
        Tuple of (vmin, vmax, stretch) where stretch is an AsinhStretch instance.
    """
    step = max(1, ny // 100)
    sample = np.array(fits_data[::step, ::step], dtype=np.float32)
    sample = np.nan_to_num(sample, nan=0.0, posinf=0.0, neginf=0.0)

    interval = ZScaleInterval()
    vmin, vmax = interval.get_limits(sample)

    stretch = AsinhStretch(a=0.1)

    logger.info(
        "Normalization parameters computed from subsample "
        "(step=%d, sample_shape=%s): vmin=%.4f, vmax=%.4f",
        step,
        sample.shape,
        vmin,
        vmax,
    )

    return float(vmin), float(vmax), stretch


def _normalize_chunk(chunk_data, vmin, vmax, stretch):
    """Normalize a chunk of FITS data to 8-bit using pre-computed parameters.

    Applies linear rescaling with pre-computed vmin/vmax, then asinh stretch,
    then converts to uint8.

    Args:
        chunk_data: Raw FITS data chunk as float32 numpy array.
        vmin: Pre-computed ZScale minimum.
        vmax: Pre-computed ZScale maximum.
        stretch: Pre-computed AsinhStretch instance.

    Returns:
        Normalized uint8 numpy array.
    """
    chunk = np.nan_to_num(chunk_data, nan=0.0, posinf=0.0, neginf=0.0)

    # Linear rescale to [0, 1] using pre-computed vmin/vmax
    if vmax > vmin:
        chunk = np.clip((chunk - vmin) / (vmax - vmin), 0, 1)
    else:
        chunk = np.zeros_like(chunk)

    # Apply asinh stretch
    chunk = stretch(chunk)

    # Convert to 8-bit
    chunk_uint8 = (chunk * 255).astype(np.uint8)

    return chunk_uint8


def _process_fits_to_tiff(fits_path, temp_dir):
    """Process a FITS file into a tiled, pyramidal TIFF using chunked reads.

    MEMORY SAFETY: Never loads the full FITS image into memory. Reads in
    CHUNK_ROWS-high bands, normalizes each band, creates pyvips strips,
    and joins them incrementally.

    Args:
        fits_path: Path to the local FITS file.
        temp_dir: Temporary directory for intermediate files.

    Returns:
        Tuple of (tiff_path, ny, nx, vmin, vmax) where tiff_path is the
        path to the generated pyramidal TIFF.
    """
    with fits.open(fits_path, memmap=True, mode="denywrite") as hdul:
        sci_hdu = _find_sci_extension(hdul)
        data = sci_hdu.data

        # Handle 3D+ FITS cubes (e.g., spectral cubes with shape (nz, ny, nx))
        # by selecting the first spectral/wavelength slice for tiling.
        if data.ndim > 2:
            logger.info(
                "FITS data has %d dimensions (shape=%s), selecting first 2D slice",
                data.ndim,
                data.shape,
            )
            # Take first slice along all extra leading dimensions
            while data.ndim > 2:
                data = data[0]

        ny, nx = data.shape

        logger.info(
            "Processing FITS image: %d x %d pixels (%.1f megapixels)",
            nx, ny, (nx * ny) / 1e6,
        )

        # Step 1: Compute normalization parameters from subsample
        vmin, vmax, stretch = _compute_normalization_parameters(data, ny, nx)

        # Step 2: Chunked normalization to pyvips strips
        strips = []
        is_large_image = ny > LARGE_IMAGE_ROW_THRESHOLD

        for y_start in range(0, ny, CHUNK_ROWS):
            y_end = min(y_start + CHUNK_ROWS, ny)
            chunk_height = y_end - y_start

            # Read chunk from memory-mapped FITS data
            chunk = np.array(data[y_start:y_end, :], dtype=np.float32)

            # Normalize using pre-computed parameters
            chunk_uint8 = _normalize_chunk(chunk, vmin, vmax, stretch)

            # Convert to pyvips image strip
            pyvips = _get_pyvips()
            strip = pyvips.Image.new_from_memory(
                chunk_uint8.tobytes(), nx, chunk_height, 1, "uchar"
            )
            strips.append(strip)

            logger.debug(
                "Processed chunk rows %d-%d of %d", y_start, y_end, ny
            )

        # Join strips vertically into full image
        if len(strips) == 1:
            full_image = strips[0]
        elif is_large_image:
            # For very large images (>50,000 rows), join incrementally to
            # avoid accumulating too many pyvips operations in memory.
            # pyvips uses lazy evaluation, so this builds a pipeline rather
            # than materializing the full image.
            full_image = strips[0]
            for strip in strips[1:]:
                full_image = full_image.join(strip, "vertical")
        else:
            # For normal-sized images, use arrayjoin which is more efficient
            # for moderate strip counts
            full_image = _get_pyvips().Image.arrayjoin(strips, across=1)

        # Save as intermediate tiled pyramidal TIFF
        temp_tiff_path = os.path.join(temp_dir, "intermediate.tif")
        full_image.tiffsave(
            temp_tiff_path,
            tile=True,
            pyramid=True,
            compression="jpeg",
            Q=85,
        )

        logger.info(
            "Saved intermediate pyramidal TIFF: %s (%.1f MB)",
            temp_tiff_path,
            os.path.getsize(temp_tiff_path) / (1024 * 1024),
        )

    return temp_tiff_path, ny, nx, vmin, vmax


def _generate_dzi_pyramid(tiff_path, temp_dir, observation_uuid_hex):
    """Generate DZI tile pyramid from a pyramidal TIFF.

    Uses pyvips dzsave to create a Deep Zoom Image tile set with 256px tiles
    and 1px overlap, suitable for OpenSeadragon or similar viewers.

    Args:
        tiff_path: Path to the intermediate pyramidal TIFF.
        temp_dir: Temporary directory for DZI output.
        observation_uuid_hex: Observation UUID for naming.

    Returns:
        Tuple of (dzi_xml_path, tiles_directory, max_zoom_level).
    """
    output_base = os.path.join(temp_dir, observation_uuid_hex)

    # Load with sequential access for efficient streaming
    pyvips = _get_pyvips()
    vips_image = pyvips.Image.new_from_file(tiff_path, access="sequential")

    # Generate DZI tile pyramid
    vips_image.dzsave(
        output_base,
        tile_size=256,
        overlap=1,
        depth="onepixel",
        suffix=".jpg[Q=85]",
        layout="dz",
    )

    dzi_xml_path = f"{output_base}.dzi"
    tiles_directory = f"{output_base}_files"

    # Calculate max zoom level from the DZI output directory structure
    max_zoom_level = 0
    if os.path.isdir(tiles_directory):
        level_dirs = [
            d for d in os.listdir(tiles_directory) if d.isdigit()
        ]
        if level_dirs:
            max_zoom_level = max(int(d) for d in level_dirs)

    logger.info(
        "Generated DZI pyramid: max_zoom_level=%d, tiles_dir=%s",
        max_zoom_level,
        tiles_directory,
    )

    return dzi_xml_path, tiles_directory, max_zoom_level


def _upload_tiles_to_minio(
    dzi_xml_path, tiles_directory, observation_uuid_hex
):
    """Upload DZI XML and all tile images to MinIO tiles bucket.

    Uploads the DZI descriptor XML and recursively walks the tiles directory
    to upload each tile JPEG with the correct content type.

    S3 key structure:
        {observation_uuid}/{observation_uuid}.dzi  (XML descriptor)
        {observation_uuid}/tiles/{level}/{col}_{row}.jpg  (tile images)

    Args:
        dzi_xml_path: Path to the .dzi XML descriptor file.
        tiles_directory: Path to the _files directory containing tile levels.
        observation_uuid_hex: Observation UUID for S3 key prefix.

    Returns:
        Tuple of (dzi_s3_key, tile_count, total_bytes_uploaded).
    """
    s3_client = get_s3_client()
    tiles_bucket = settings.s3_bucket_tiles

    tile_count = 0
    total_bytes_uploaded = 0

    # Upload DZI XML descriptor
    dzi_s3_key = f"{observation_uuid_hex}/{observation_uuid_hex}.dzi"
    dzi_size = os.path.getsize(dzi_xml_path)

    s3_client.upload_file(
        dzi_xml_path,
        tiles_bucket,
        dzi_s3_key,
        ExtraArgs={"ContentType": "application/xml"},
    )
    total_bytes_uploaded += dzi_size

    logger.info(
        "Uploaded DZI descriptor to s3://%s/%s (%d bytes)",
        tiles_bucket,
        dzi_s3_key,
        dzi_size,
    )

    # Walk tiles directory and upload each tile
    for dirpath, _dirnames, filenames in os.walk(tiles_directory):
        for filename in filenames:
            if not filename.endswith(".jpg"):
                continue

            local_file_path = os.path.join(dirpath, filename)
            file_size = os.path.getsize(local_file_path)

            # Extract level from directory structure
            # tiles_directory/{level}/{col}_{row}.jpg
            relative_path = os.path.relpath(local_file_path, tiles_directory)
            s3_key = f"{observation_uuid_hex}/tiles/{relative_path}"

            s3_client.upload_file(
                local_file_path,
                tiles_bucket,
                s3_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )

            tile_count += 1
            total_bytes_uploaded += file_size

    logger.info(
        "Uploaded %d tiles (%.1f MB total) to s3://%s/%s/tiles/",
        tile_count,
        total_bytes_uploaded / (1024 * 1024),
        tiles_bucket,
        observation_uuid_hex,
    )

    return dzi_s3_key, tile_count, total_bytes_uploaded


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def generate_tiles(self, wcs_result: dict) -> dict:
    """Generate DZI tile pyramids from FITS data and upload to MinIO.

    Receives the output dict from validate_wcs, downloads each FITS file from
    MinIO, normalizes the science data using ZScale + asinh stretch (parameters
    computed from a subsample), generates DZI tile pyramids via pyvips, and
    uploads the tiles to the MinIO tiles bucket.

    Memory safety: FITS data is processed in CHUNK_ROWS-high row bands.
    The full image is never loaded into memory at once. Normalization parameters
    are computed once from a subsample and applied consistently to all chunks.

    Args:
        wcs_result: Dict from validate_wcs containing:
            - observation_uuid: hex string of observation UUID
            - fits_s3_keys: list of S3 keys for FITS files in fits-raw bucket
            - wcs_valid: whether WCS validation passed
            - image_dimensions: dict with ny, nx (or None)

    Returns:
        Dict with observation_uuid, tile_count, dzi_s3_key, and status.
    """
    observation_uuid_hex = wcs_result["observation_uuid"]
    fits_s3_keys = wcs_result["fits_s3_keys"]
    observation_uuid = uuid.UUID(observation_uuid_hex)

    database_session = SessionLocal()
    processing_step = None
    temp_dir = None

    try:
        # --- Step a: Create ProcessingStep record ---
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="generate_tiles",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        logger.info(
            "Starting tile generation for observation %s (%d FITS files)",
            observation_uuid_hex,
            len(fits_s3_keys),
        )

        s3_client = get_s3_client()
        temp_dir = tempfile.mkdtemp(prefix="tiles_")

        total_tile_count = 0
        total_bytes_uploaded = 0
        dzi_s3_key = None
        max_zoom_level = 0
        image_width_pixels = 0
        image_height_pixels = 0
        normalization_vmin = 0.0
        normalization_vmax = 0.0

        # --- Step b: Process each FITS file ---
        for fits_index, fits_s3_key in enumerate(fits_s3_keys):
            logger.info(
                "Processing FITS file %d/%d: %s",
                fits_index + 1,
                len(fits_s3_keys),
                fits_s3_key,
            )

            # Download FITS from MinIO to local temp file
            temp_fits_path = os.path.join(temp_dir, f"input_{fits_index}.fits")
            s3_client.download_file(
                settings.s3_bucket_fits_raw,
                fits_s3_key,
                temp_fits_path,
            )

            # Step 1-2: Process FITS to intermediate pyramidal TIFF
            tiff_path, ny, nx, vmin, vmax = _process_fits_to_tiff(
                temp_fits_path, temp_dir
            )

            # Track dimensions and normalization from primary file
            if fits_index == 0:
                image_height_pixels = ny
                image_width_pixels = nx
                normalization_vmin = vmin
                normalization_vmax = vmax

            # Step 3: Generate DZI tile pyramid
            dzi_xml_path, tiles_directory, zoom_level = _generate_dzi_pyramid(
                tiff_path, temp_dir, observation_uuid_hex
            )

            max_zoom_level = max(max_zoom_level, zoom_level)

            # Step 4: Upload tiles to MinIO
            file_dzi_s3_key, tile_count, bytes_uploaded = (
                _upload_tiles_to_minio(
                    dzi_xml_path, tiles_directory, observation_uuid_hex
                )
            )

            if fits_index == 0:
                dzi_s3_key = file_dzi_s3_key

            total_tile_count += tile_count
            total_bytes_uploaded += bytes_uploaded

            # Clean up intermediate files for this FITS file to free disk space
            try:
                os.unlink(temp_fits_path)
            except OSError:
                pass
            try:
                os.unlink(tiff_path)
            except OSError:
                pass
            if os.path.isdir(tiles_directory):
                shutil.rmtree(tiles_directory, ignore_errors=True)
            try:
                os.unlink(dzi_xml_path)
            except OSError:
                pass

        # --- Step 5: Record metadata and update records ---
        step_output_metadata = {
            "tile_count": total_tile_count,
            "max_zoom_level": max_zoom_level,
            "tile_size_pixels": 256,
            "dzi_s3_key": dzi_s3_key,
            "normalization_vmin": normalization_vmin,
            "normalization_vmax": normalization_vmax,
            "image_width_pixels": image_width_pixels,
            "image_height_pixels": image_height_pixels,
            "total_bytes_uploaded": total_bytes_uploaded,
            "files_processed": len(fits_s3_keys),
        }

        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = step_output_metadata
        database_session.commit()

        # Pipeline continues to segmentation — do NOT set completed here.
        # The final task in the chain (generate_cutouts, Plan 04-03) sets completed.
        logger.info(
            "Tile generation complete — pipeline continues to segmentation "
            "for observation %s",
            observation_uuid_hex,
        )

        logger.info(
            "Tile generation completed for observation %s: "
            "%d tiles, %d zoom levels, %.1f MB uploaded",
            observation_uuid_hex,
            total_tile_count,
            max_zoom_level,
            total_bytes_uploaded / (1024 * 1024),
        )

        # --- Step d: Return result ---
        return {
            "observation_uuid": observation_uuid_hex,
            "tile_count": total_tile_count,
            "dzi_s3_key": dzi_s3_key,
            "status": "completed",
        }

    except Exception as exception:
        logger.exception(
            "Tile generation failed for observation %s: %s",
            observation_uuid_hex,
            exception,
        )

        # --- Step c: Mark processing step and observation as failed ---
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

        database_session.close()
