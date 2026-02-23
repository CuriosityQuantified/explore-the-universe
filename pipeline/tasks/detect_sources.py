"""Multi-scale SEP source detection Celery task.

Runs SEP (Source Extractor as a Python library) source detection at three
scales -- full field, sub-regions (1024px), and sub-sub-regions (256px) --
with 20% overlap between sub-regions. Each detected source is assigned a
confidence tier (high/medium/low) based on SNR from Kron photometry, flagged
if touching a boundary, and converted to WCS sky coordinates.

Creates AstronomicalObject records in PostgreSQL for every detection across
all scales. This is the fourth step in the pipeline chain, receiving output
from generate_tiles and passing results to segment_sam.

Usage:
    # Called as part of Celery chain (receives generate_tiles output dict)
    detect_sources({"observation_uuid": "...", "tile_count": N, ...})
"""

import logging
import os
import tempfile
import uuid

import numpy as np
import sep
from astropy.io import fits
from astropy.wcs import WCS
from sqlalchemy import func as sql_func

from api.db.session import SessionLocal
from pipeline.celery_app import celery_app
from shared.config import settings
from shared.models import (
    AstronomicalObject,
    DetectionConfidenceTier,
    Observation,
    PipelineStatus,
    ProcessingStep,
    StepStatus,
)
from shared.s3 import get_s3_client

logger = logging.getLogger(__name__)

# Maximum detections at a single scale before logging a warning.
MAX_DETECTIONS_WARNING_THRESHOLD = 50_000

# Pixel distance from boundary to classify a detection as "edge".
EDGE_BOUNDARY_PIXELS = 5


def _find_sci_extension(hdul):
    """Find the SCI extension in a FITS HDU list.

    Same logic as validate_wcs._find_sci_extension -- checks for named 'SCI'
    extension first (JWST MEF standard), falls back to primary HDU. Copied
    here (not imported) to avoid circular dependency between task modules.

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


def _fix_byte_order(data: np.ndarray) -> np.ndarray:
    """Ensure data is in native byte order and float32 for SEP.

    FITS files are big-endian. SEP's C backend requires native byte order
    (little-endian on x86/ARM). This function converts if necessary and
    always casts to float32.

    Args:
        data: Input numpy array from FITS (may be big-endian float64/float32).

    Returns:
        float32 array in native byte order.
    """
    if data.dtype.byteorder not in ("=", "<", "|"):
        # np.array with explicit dtype handles byteswap automatically.
        # ndarray.newbyteorder() was removed in numpy 2.x.
        data = np.array(data, dtype=np.float32)
        return data
    return data.astype(np.float32, copy=False)


def _detect_sources_in_array(
    data: np.ndarray,
) -> tuple[np.ndarray, "sep.Background", np.ndarray]:
    """Run SEP background estimation and source extraction on a 2D array.

    Args:
        data: 2D float32 array in native byte order.

    Returns:
        Tuple of (objects_structured_array, background, background_subtracted_data).
    """
    background = sep.Background(
        data,
        bw=settings.segmentation_background_box_size,
        bh=settings.segmentation_background_box_size,
        fw=3,
        fh=3,
    )
    data_subtracted = data - background.back()

    objects = sep.extract(
        data_subtracted,
        thresh=settings.segmentation_detection_threshold_sigma,
        err=background.globalrms,
        minarea=settings.segmentation_min_area_pixels,
        deblend_nthresh=settings.segmentation_deblend_nthresh,
        deblend_cont=settings.segmentation_deblend_contrast,
    )

    return objects, background, data_subtracted


def _compute_kron_photometry(
    data_subtracted: np.ndarray,
    background: "sep.Background",
    objects: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute Kron radius photometry for better flux/SNR estimates.

    Args:
        data_subtracted: Background-subtracted 2D float32 array.
        background: SEP Background object for global RMS.
        objects: SEP structured array of detected sources.

    Returns:
        Tuple of (flux_array, flux_error_array).
    """
    kron_radius, kron_flag = sep.kron_radius(
        data_subtracted,
        objects["x"],
        objects["y"],
        objects["a"],
        objects["b"],
        objects["theta"],
        6.0,
    )

    # Handle edge cases where kron_radius might be 0, NaN, or negative.
    kron_radius = np.where(
        np.isfinite(kron_radius) & (kron_radius > 0), kron_radius, 1.0
    )
    kron_radius = np.maximum(kron_radius, 1.0)

    flux, flux_error, flux_flag = sep.sum_ellipse(
        data_subtracted,
        objects["x"],
        objects["y"],
        objects["a"],
        objects["b"],
        objects["theta"],
        2.5 * kron_radius,
        err=background.globalrms,
        subpix=1,
    )

    return flux, flux_error


def _assign_confidence_tiers(
    flux: np.ndarray,
    flux_error: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Assign detection confidence tiers based on signal-to-noise ratio.

    SNR = flux / flux_error. Where flux_error is 0, SNR is set to 0.

    Tiers:
        - SNR >= segmentation_snr_high_threshold (10.0) -> "high"
        - SNR >= segmentation_snr_medium_threshold (3.0) -> "medium"
        - Below -> "low"

    Args:
        flux: Array of flux values from Kron photometry.
        flux_error: Array of flux error values.

    Returns:
        Tuple of (tier_strings_array, snr_array).
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        signal_to_noise_ratio = np.where(
            flux_error > 0, flux / flux_error, 0.0
        )

    tiers = np.where(
        signal_to_noise_ratio >= settings.segmentation_snr_high_threshold,
        "high",
        np.where(
            signal_to_noise_ratio >= settings.segmentation_snr_medium_threshold,
            "medium",
            "low",
        ),
    )

    return tiers, signal_to_noise_ratio


def _flag_edge_detections(
    objects: np.ndarray,
    image_height: int,
    image_width: int,
    sub_region_origin_x: int,
    sub_region_origin_y: int,
    sub_region_width: int,
    sub_region_height: int,
) -> np.ndarray:
    """Flag detections whose bounding boxes touch sub-region or image boundaries.

    An object is "edge" if its approximate bounding box (centroid +/- 3*a for x,
    centroid +/- 3*b for y) falls within EDGE_BOUNDARY_PIXELS of the sub-region
    boundary OR the full image boundary.

    Coordinates here are in sub-region-local space. Full-image boundary checking
    uses the sub_region_origin offsets to convert to global coords.

    Args:
        objects: SEP structured array with 'x', 'y', 'a', 'b' fields.
        image_height: Full image height in pixels.
        image_width: Full image width in pixels.
        sub_region_origin_x: X offset of sub-region within full image.
        sub_region_origin_y: Y offset of sub-region within full image.
        sub_region_width: Width of the sub-region being processed.
        sub_region_height: Height of the sub-region being processed.

    Returns:
        Boolean array, True for edge detections.
    """
    extent_x = 3.0 * objects["a"]
    extent_y = 3.0 * objects["b"]

    local_x_min = objects["x"] - extent_x
    local_x_max = objects["x"] + extent_x
    local_y_min = objects["y"] - extent_y
    local_y_max = objects["y"] + extent_y

    # Check sub-region boundaries (local coords)
    near_sub_left = local_x_min < EDGE_BOUNDARY_PIXELS
    near_sub_right = local_x_max > (sub_region_width - EDGE_BOUNDARY_PIXELS)
    near_sub_top = local_y_min < EDGE_BOUNDARY_PIXELS
    near_sub_bottom = local_y_max > (sub_region_height - EDGE_BOUNDARY_PIXELS)

    near_sub_boundary = near_sub_left | near_sub_right | near_sub_top | near_sub_bottom

    # Check full-image boundaries (global coords)
    global_x_min = local_x_min + sub_region_origin_x
    global_x_max = local_x_max + sub_region_origin_x
    global_y_min = local_y_min + sub_region_origin_y
    global_y_max = local_y_max + sub_region_origin_y

    near_image_left = global_x_min < EDGE_BOUNDARY_PIXELS
    near_image_right = global_x_max > (image_width - EDGE_BOUNDARY_PIXELS)
    near_image_top = global_y_min < EDGE_BOUNDARY_PIXELS
    near_image_bottom = global_y_max > (image_height - EDGE_BOUNDARY_PIXELS)

    near_image_boundary = (
        near_image_left | near_image_right | near_image_top | near_image_bottom
    )

    return near_sub_boundary | near_image_boundary


def _extract_sub_regions(
    image_height: int,
    image_width: int,
    region_size: int,
    overlap_fraction: float,
) -> list[tuple[int, int, int, int]]:
    """Generate list of sub-region coordinates for tiled detection.

    Returns (y_start, y_end, x_start, x_end) tuples with overlapping tiles.
    Returns empty list if image is smaller than region_size in both dimensions.

    Args:
        image_height: Image height in pixels.
        image_width: Image width in pixels.
        region_size: Target sub-region size in pixels.
        overlap_fraction: Fraction of overlap between adjacent sub-regions.

    Returns:
        List of (y_start, y_end, x_start, x_end) tuples.
    """
    if image_height < region_size and image_width < region_size:
        return []

    overlap_pixels = int(region_size * overlap_fraction)
    stride = region_size - overlap_pixels

    regions = []
    y_start = 0
    while y_start < image_height:
        y_end = min(y_start + region_size, image_height)
        x_start = 0
        while x_start < image_width:
            x_end = min(x_start + region_size, image_width)
            regions.append((y_start, y_end, x_start, x_end))
            if x_end >= image_width:
                break
            x_start += stride
        if y_end >= image_height:
            break
        y_start += stride

    return regions


def _run_multi_scale_detection(
    fits_data: np.ndarray,
    wcs_object: WCS,
    observation_uuid: uuid.UUID,
    database_session,
) -> list[uuid.UUID]:
    """Core multi-scale detection loop across three scale levels.

    Scale 1: Full field detection.
    Scale 2: Sub-regions (1024px with 20% overlap) -- skipped if image
             is smaller than 1.5x the sub-region size in both dimensions.
    Scale 3: Sub-sub-regions (256px with 20% overlap) -- only processes
             sub-regions that had detections.

    For every detection at every scale, creates an AstronomicalObject record
    with pixel centroids, WCS sky coordinates, confidence tier, bounding box,
    edge flag, SNR, and SEP ellipse parameters in physical_properties.

    Args:
        fits_data: 2D float32 array in native byte order.
        wcs_object: Astropy WCS for pixel-to-sky conversion.
        observation_uuid: UUID of the parent observation.
        database_session: SQLAlchemy session (caller commits).

    Returns:
        List of created AstronomicalObject UUIDs.
    """
    image_height, image_width = fits_data.shape
    all_object_uuids = []
    scale_counts = {"full_field": 0, "sub_region": 0, "sub_sub_region": 0}

    # --- Scale 1: Full field ---
    logger.info(
        "Scale 1 (full_field): detecting sources in %dx%d image",
        image_width,
        image_height,
    )
    full_field_uuids = _detect_and_store(
        fits_data,
        wcs_object,
        observation_uuid,
        database_session,
        detection_scale_level="full_field",
        sub_region_origin_x=0,
        sub_region_origin_y=0,
        image_height=image_height,
        image_width=image_width,
    )
    all_object_uuids.extend(full_field_uuids)
    scale_counts["full_field"] = len(full_field_uuids)

    # --- Scale 2: Sub-regions ---
    sub_region_size = settings.segmentation_sub_region_size
    min_dimension_for_sub_regions = int(sub_region_size * 1.5)

    if (
        image_height >= min_dimension_for_sub_regions
        or image_width >= min_dimension_for_sub_regions
    ):
        sub_regions = _extract_sub_regions(
            image_height,
            image_width,
            sub_region_size,
            settings.segmentation_overlap_fraction,
        )
        logger.info(
            "Scale 2 (sub_region): %d sub-regions of %dpx with %.0f%% overlap",
            len(sub_regions),
            sub_region_size,
            settings.segmentation_overlap_fraction * 100,
        )

        sub_regions_with_detections = []
        for region_index, (y_start, y_end, x_start, x_end) in enumerate(
            sub_regions
        ):
            sub_array = fits_data[y_start:y_end, x_start:x_end]
            if sub_array.size == 0:
                continue

            region_uuids = _detect_and_store(
                sub_array,
                wcs_object,
                observation_uuid,
                database_session,
                detection_scale_level="sub_region",
                sub_region_origin_x=x_start,
                sub_region_origin_y=y_start,
                image_height=image_height,
                image_width=image_width,
            )
            all_object_uuids.extend(region_uuids)
            scale_counts["sub_region"] += len(region_uuids)

            if len(region_uuids) > 0:
                sub_regions_with_detections.append(
                    (y_start, y_end, x_start, x_end)
                )

        # --- Scale 3: Sub-sub-regions (only where sub-regions had detections) ---
        sub_sub_region_size = settings.segmentation_sub_sub_region_size
        if sub_regions_with_detections:
            logger.info(
                "Scale 3 (sub_sub_region): subdividing %d active sub-regions "
                "into %dpx sub-sub-regions",
                len(sub_regions_with_detections),
                sub_sub_region_size,
            )
            for y_start, y_end, x_start, x_end in sub_regions_with_detections:
                parent_height = y_end - y_start
                parent_width = x_end - x_start

                sub_sub_regions = _extract_sub_regions(
                    parent_height,
                    parent_width,
                    sub_sub_region_size,
                    settings.segmentation_overlap_fraction,
                )

                for (
                    local_y_start,
                    local_y_end,
                    local_x_start,
                    local_x_end,
                ) in sub_sub_regions:
                    global_y_start = y_start + local_y_start
                    global_y_end = y_start + local_y_end
                    global_x_start = x_start + local_x_start
                    global_x_end = x_start + local_x_end

                    sub_sub_array = fits_data[
                        global_y_start:global_y_end,
                        global_x_start:global_x_end,
                    ]
                    if sub_sub_array.size == 0:
                        continue

                    ssub_uuids = _detect_and_store(
                        sub_sub_array,
                        wcs_object,
                        observation_uuid,
                        database_session,
                        detection_scale_level="sub_sub_region",
                        sub_region_origin_x=global_x_start,
                        sub_region_origin_y=global_y_start,
                        image_height=image_height,
                        image_width=image_width,
                    )
                    all_object_uuids.extend(ssub_uuids)
                    scale_counts["sub_sub_region"] += len(ssub_uuids)
    else:
        logger.info(
            "Scale 2/3 skipped: image %dx%d is smaller than 1.5x sub-region "
            "size (%d)",
            image_width,
            image_height,
            sub_region_size,
        )

    logger.info(
        "Multi-scale detection complete: %d total objects "
        "(full_field=%d, sub_region=%d, sub_sub_region=%d)",
        len(all_object_uuids),
        scale_counts["full_field"],
        scale_counts["sub_region"],
        scale_counts["sub_sub_region"],
    )

    return all_object_uuids


def _detect_and_store(
    data: np.ndarray,
    wcs_object: WCS,
    observation_uuid: uuid.UUID,
    database_session,
    detection_scale_level: str,
    sub_region_origin_x: int,
    sub_region_origin_y: int,
    image_height: int,
    image_width: int,
) -> list[uuid.UUID]:
    """Run SEP detection on a data array and store results in the database.

    Runs detection, Kron photometry, confidence tier assignment, edge flagging,
    and WCS coordinate conversion. Creates AstronomicalObject records for each
    detection. The caller is responsible for committing the session.

    Args:
        data: 2D float32 array (sub-region or full field).
        wcs_object: Astropy WCS for full-image pixel-to-sky conversion.
        observation_uuid: UUID of the parent observation.
        database_session: SQLAlchemy session.
        detection_scale_level: One of "full_field", "sub_region", "sub_sub_region".
        sub_region_origin_x: X offset of this region in full-image coords.
        sub_region_origin_y: Y offset of this region in full-image coords.
        image_height: Full image height.
        image_width: Full image width.

    Returns:
        List of created AstronomicalObject UUIDs.
    """
    sub_region_height, sub_region_width = data.shape

    try:
        objects, background, data_subtracted = _detect_sources_in_array(data)
    except Exception as detection_error:
        logger.warning(
            "SEP detection failed on %s region at (%d, %d): %s",
            detection_scale_level,
            sub_region_origin_x,
            sub_region_origin_y,
            detection_error,
        )
        return []

    if len(objects) == 0:
        return []

    if len(objects) > MAX_DETECTIONS_WARNING_THRESHOLD:
        logger.warning(
            "%s detection at (%d, %d) found %d sources (exceeds %d threshold)",
            detection_scale_level,
            sub_region_origin_x,
            sub_region_origin_y,
            len(objects),
            MAX_DETECTIONS_WARNING_THRESHOLD,
        )

    # Kron photometry
    flux, flux_error = _compute_kron_photometry(
        data_subtracted, background, objects
    )

    # Confidence tiers
    tiers, signal_to_noise_ratios = _assign_confidence_tiers(flux, flux_error)

    # Edge flags
    edge_flags = _flag_edge_detections(
        objects,
        image_height,
        image_width,
        sub_region_origin_x,
        sub_region_origin_y,
        sub_region_width,
        sub_region_height,
    )

    # Create AstronomicalObject records
    created_uuids = []
    new_objects = []

    for i in range(len(objects)):
        # Convert sub-region-local pixel coords to full-image global coords
        global_centroid_x = float(objects["x"][i]) + sub_region_origin_x
        global_centroid_y = float(objects["y"][i]) + sub_region_origin_y

        # Convert pixel centroid to RA/Dec via WCS
        sky_coord = wcs_object.pixel_to_world(global_centroid_x, global_centroid_y)
        ra_degrees = float(sky_coord.ra.deg)
        dec_degrees = float(sky_coord.dec.deg)

        # Bounding box in full-image coords
        extent_x = 3.0 * float(objects["a"][i])
        extent_y = 3.0 * float(objects["b"][i])
        bounding_box = {
            "xmin": max(0, int(global_centroid_x - extent_x)),
            "ymin": max(0, int(global_centroid_y - extent_y)),
            "xmax": min(image_width, int(global_centroid_x + extent_x)),
            "ymax": min(image_height, int(global_centroid_y + extent_y)),
        }

        # Map tier string to enum
        tier_string = str(tiers[i])
        confidence_tier_enum = DetectionConfidenceTier(tier_string)

        # SEP ellipse params in physical_properties for segment_sam fallback
        physical_properties = {
            "sep_a": float(objects["a"][i]),
            "sep_b": float(objects["b"][i]),
            "sep_theta": float(objects["theta"][i]),
            "sep_flux": float(flux[i]),
        }

        object_uuid = uuid.uuid4()
        astronomical_object = AstronomicalObject(
            object_uuid=object_uuid,
            source_observation_uuid=observation_uuid,
            sky_coordinate_ra_degrees=ra_degrees,
            sky_coordinate_dec_degrees=dec_degrees,
            pixel_centroid_x=global_centroid_x,
            pixel_centroid_y=global_centroid_y,
            bounding_box_pixels=bounding_box,
            detection_signal_to_noise_ratio=float(signal_to_noise_ratios[i]),
            detection_confidence_tier=confidence_tier_enum,
            detection_scale_level=detection_scale_level,
            is_edge_detection=bool(edge_flags[i]),
            physical_properties=physical_properties,
        )
        new_objects.append(astronomical_object)
        created_uuids.append(object_uuid)

    database_session.add_all(new_objects)
    database_session.flush()

    logger.debug(
        "%s at (%d, %d): %d detections stored",
        detection_scale_level,
        sub_region_origin_x,
        sub_region_origin_y,
        len(created_uuids),
    )

    return created_uuids


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def detect_sources(self, tile_result: dict) -> dict:
    """Run multi-scale SEP source detection on a FITS observation.

    Receives the output dict from generate_tiles, downloads the first FITS
    file from MinIO, runs three-scale SEP detection (full field, sub-regions,
    sub-sub-regions), assigns confidence tiers via Kron photometry SNR, flags
    edge detections, converts pixel centroids to RA/Dec via WCS, and creates
    AstronomicalObject records in the database.

    Data flow:
        tile_result["observation_uuid"] -> observation UUID
        tile_result["fits_s3_keys"] (from upstream) -> FITS download

    Note: tile_result comes from generate_tiles which does not include
    fits_s3_keys. However, the ingest chain passes data through, and
    generate_tiles returns observation_uuid. We re-query the ProcessingStep
    for the download step to get fits_s3_keys if not present.

    Args:
        tile_result: Dict from generate_tiles containing at minimum
            observation_uuid.

    Returns:
        Dict with observation_uuid, fits_s3_keys, source_count, object_uuids.
    """
    observation_uuid_hex = tile_result["observation_uuid"]
    observation_uuid = uuid.UUID(observation_uuid_hex)

    # fits_s3_keys may come from upstream chain or need recovery from DB
    fits_s3_keys = tile_result.get("fits_s3_keys")

    database_session = SessionLocal()
    processing_step = None
    temp_fits_path = None

    try:
        # If fits_s3_keys not in tile_result, recover from download step metadata
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
                    f"No fits_s3_keys available for observation {observation_uuid_hex}"
                )

        # Create ProcessingStep record
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="detect_sources",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        logger.info(
            "Starting multi-scale source detection for observation %s",
            observation_uuid_hex,
        )

        # Download first FITS file from MinIO
        s3_client = get_s3_client()
        temp_fd, temp_fits_path = tempfile.mkstemp(suffix=".fits")
        os.close(temp_fd)

        s3_client.download_file(
            settings.s3_bucket_fits_raw,
            fits_s3_keys[0],
            temp_fits_path,
        )

        # Open FITS and extract 2D science data + WCS
        with fits.open(temp_fits_path, memmap=True, mode="denywrite") as hdul:
            sci_hdu = _find_sci_extension(hdul)
            data = sci_hdu.data

            # Handle 3D+ FITS cubes: take first 2D slice
            if data.ndim > 2:
                logger.info(
                    "FITS data has %d dimensions (shape=%s), selecting first 2D slice",
                    data.ndim,
                    data.shape,
                )
                while data.ndim > 2:
                    data = data[0]

            # Get WCS, use celestial sub-WCS for 3D+
            full_wcs = WCS(sci_hdu.header)
            if full_wcs.naxis > 2:
                wcs_object = full_wcs.celestial
            else:
                wcs_object = full_wcs

            # Fix byte order and cast to float32
            data = np.array(data, dtype=np.float32)
            data = _fix_byte_order(data)

            # Run multi-scale detection
            object_uuids = _run_multi_scale_detection(
                data,
                wcs_object,
                observation_uuid,
                database_session,
            )

        # Count by scale level
        scale_counts = {"full_field": 0, "sub_region": 0, "sub_sub_region": 0}
        for obj_uuid in object_uuids:
            obj_record = (
                database_session.query(AstronomicalObject.detection_scale_level)
                .filter(AstronomicalObject.object_uuid == obj_uuid)
                .first()
            )
            if obj_record and obj_record[0] in scale_counts:
                scale_counts[obj_record[0]] += 1

        # Update ProcessingStep to completed
        step_output_metadata = {
            "source_count": len(object_uuids),
            "scale_counts": scale_counts,
        }
        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = step_output_metadata
        database_session.commit()

        logger.info(
            "Source detection completed for observation %s: %d objects "
            "(full_field=%d, sub_region=%d, sub_sub_region=%d)",
            observation_uuid_hex,
            len(object_uuids),
            scale_counts["full_field"],
            scale_counts["sub_region"],
            scale_counts["sub_sub_region"],
        )

        return {
            "observation_uuid": observation_uuid_hex,
            "fits_s3_keys": fits_s3_keys,
            "source_count": len(object_uuids),
            "object_uuids": [str(u) for u in object_uuids],
        }

    except Exception as exception:
        logger.exception(
            "Source detection failed for observation %s: %s",
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
        # Clean up temp files
        if temp_fits_path is not None:
            try:
                os.unlink(temp_fits_path)
            except OSError:
                pass

        database_session.close()
