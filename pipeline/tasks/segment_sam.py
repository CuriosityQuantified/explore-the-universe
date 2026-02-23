"""SAM 3 segmentation with SEP elliptical fallback Celery task.

Generates pixel-level segmentation masks for all detected astronomical objects.
When CUDA is available, uses Meta's SAM 3 model for high-quality masks from
point and box prompts derived from SEP detections. When CUDA is unavailable,
falls back to SEP elliptical aperture masks generated from the stored a, b,
theta parameters.

All masks are encoded in COCO RLE format (pycocotools) and stored in the
AstronomicalObject.segmentation_mask_rle JSONB column. After segmentation,
objects in overlapping sub-region zones are merged via IoU matching to remove
duplicate detections.

This is the fifth step in the pipeline chain, receiving output from
detect_sources and passing results to generate_cutouts.

Usage:
    # Called as part of Celery chain (receives detect_sources output dict)
    segment_sam({"observation_uuid": "...", "source_count": N, ...})
"""

import logging
import os
import tempfile
import uuid

import numpy as np
import pycocotools.mask as mask_util
from astropy.io import fits
from astropy.visualization import AsinhStretch, ZScaleInterval
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

# Scaling factor for elliptical mask semi-axes (approximation of Kron radius).
ELLIPSE_MASK_KRON_FACTOR = 3.0

# Maximum image dimension for SAM processing. Larger images use SEP elliptical
# masks for full-field detections.
SAM_MAX_IMAGE_DIMENSION = 1024

# Module-level SAM singleton state
_sam_processor = None
_sam_available = None


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


def _get_sam_processor():
    """Lazily initialize SAM 3 model and processor.

    Returns Sam3Processor if CUDA is available and SAM 3 can be loaded.
    Returns None otherwise. Uses module-level singleton -- only one
    initialization attempt per process.

    Returns:
        Sam3Processor instance or None if SAM 3 is unavailable.
    """
    global _sam_processor, _sam_available

    if _sam_available is False:
        return None

    if _sam_processor is not None:
        return _sam_processor

    try:
        import torch

        if not torch.cuda.is_available():
            logger.warning(
                "CUDA not available -- SAM 3 segmentation disabled, "
                "using SEP elliptical masks only"
            )
            _sam_available = False
            return None

        from sam3 import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor

        bpe_path = settings.sam3_bpe_path if settings.sam3_bpe_path else None
        model = build_sam3_image_model(
            bpe_path=bpe_path, enable_inst_interactivity=True
        )
        _sam_processor = Sam3Processor(model)
        _sam_available = True
        logger.info("SAM 3 initialized on %s", torch.cuda.get_device_name(0))
        return _sam_processor

    except Exception as init_error:
        logger.warning(
            "SAM 3 initialization failed: %s -- using SEP elliptical masks only",
            init_error,
        )
        _sam_available = False
        return None


def _fits_to_sam_rgb(
    fits_data: np.ndarray, vmin: float, vmax: float
) -> np.ndarray:
    """Convert FITS float32 data to SAM-compatible uint8 RGB.

    Applies ZScale + asinh stretch (same normalization approach as tile.py),
    then replicates the single channel to 3-channel RGB.

    Args:
        fits_data: 2D float32 array.
        vmin: Pre-computed ZScale minimum.
        vmax: Pre-computed ZScale maximum.

    Returns:
        uint8 array of shape (H, W, 3).
    """
    data = np.nan_to_num(fits_data, nan=0.0, posinf=0.0, neginf=0.0)

    # Linear rescale to [0, 1]
    if vmax > vmin:
        normalized = np.clip((data - vmin) / (vmax - vmin), 0, 1)
    else:
        normalized = np.zeros_like(data)

    # Asinh stretch
    stretch = AsinhStretch(a=0.1)
    stretched = stretch(normalized)

    # Scale to uint8
    uint8_data = (stretched * 255).astype(np.uint8)

    # Replicate to 3-channel RGB
    rgb = np.stack([uint8_data, uint8_data, uint8_data], axis=-1)

    return rgb


def _generate_sam_masks(
    processor, image_rgb: np.ndarray, detections: list[dict]
) -> list[np.ndarray | None]:
    """Generate SAM 3 masks for a batch of detections.

    Uses point prompts (centroids) and box prompts (bounding boxes) from
    SEP detections. Falls back to None for individual detections where
    SAM fails.

    Args:
        processor: Sam3Processor instance.
        image_rgb: uint8 RGB array of shape (H, W, 3).
        detections: List of dicts with 'centroid_x', 'centroid_y',
                    'bbox' (dict with xmin/ymin/xmax/ymax) -- all in
                    local (sub-region) coordinates.

    Returns:
        List of binary mask arrays (bool, H x W) or None for failed detections.
    """
    from PIL import Image

    pil_image = Image.fromarray(image_rgb)
    inference_state = processor.set_image(pil_image)

    masks = []
    for detection in detections:
        try:
            point_coords = np.array(
                [[detection["centroid_x"], detection["centroid_y"]]],
                dtype=np.float32,
            )
            point_labels = np.array([1], dtype=np.int32)

            bbox = detection["bbox"]
            box = np.array(
                [bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]],
                dtype=np.float32,
            )

            mask_output, scores, _ = processor.model.predict_inst(
                inference_state,
                point_coords=point_coords,
                labels=point_labels,
                box=box,
                multimask_output=False,
            )

            # Extract best mask
            if mask_output is not None and len(mask_output) > 0:
                best_mask = mask_output[0].squeeze()
                if hasattr(best_mask, "cpu"):
                    best_mask = best_mask.cpu().numpy()
                masks.append(best_mask.astype(bool))
            else:
                masks.append(None)

        except Exception as sam_error:
            logger.warning(
                "SAM prediction failed for detection at (%.1f, %.1f): %s",
                detection["centroid_x"],
                detection["centroid_y"],
                sam_error,
            )
            masks.append(None)

    return masks


def _generate_elliptical_mask(
    image_shape: tuple[int, int],
    centroid_x: float,
    centroid_y: float,
    semi_major_a: float,
    semi_minor_b: float,
    theta_radians: float,
) -> np.ndarray:
    """Generate a binary elliptical aperture mask from SEP parameters.

    Creates a rotated ellipse mask using the SEP ellipse parameters (a, b,
    theta) scaled by ELLIPSE_MASK_KRON_FACTOR to approximate the Kron aperture.

    Args:
        image_shape: (height, width) of the output mask.
        centroid_x: X coordinate of ellipse center.
        centroid_y: Y coordinate of ellipse center.
        semi_major_a: SEP semi-major axis 'a' parameter.
        semi_minor_b: SEP semi-minor axis 'b' parameter.
        theta_radians: SEP rotation angle theta in radians.

    Returns:
        Boolean mask array of shape (height, width).
    """
    height, width = image_shape

    # Scale semi-axes by Kron factor
    scaled_a = semi_major_a * ELLIPSE_MASK_KRON_FACTOR
    scaled_b = semi_minor_b * ELLIPSE_MASK_KRON_FACTOR

    # Prevent degenerate ellipses
    scaled_a = max(scaled_a, 1.0)
    scaled_b = max(scaled_b, 1.0)

    # Create coordinate grids
    y_grid, x_grid = np.ogrid[0:height, 0:width]

    # Compute rotated coordinates relative to centroid
    cos_theta = np.cos(theta_radians)
    sin_theta = np.sin(theta_radians)

    dx = x_grid - centroid_x
    dy = y_grid - centroid_y

    x_rotated = dx * cos_theta + dy * sin_theta
    y_rotated = -dx * sin_theta + dy * cos_theta

    # Evaluate ellipse equation
    ellipse_value = (x_rotated / scaled_a) ** 2 + (y_rotated / scaled_b) ** 2
    mask = ellipse_value <= 1.0

    return mask


def _encode_mask_to_rle(binary_mask: np.ndarray) -> dict:
    """Encode a binary mask to COCO RLE format.

    Uses pycocotools for standard COCO RLE encoding. The mask must be
    converted to Fortran order (column-major) as required by pycocotools.

    Args:
        binary_mask: 2D bool/uint8 array of shape (H, W).

    Returns:
        Dict with 'size' [H, W] and 'counts' (str, JSON-safe).
    """
    fortran_mask = np.asfortranarray(binary_mask.astype(np.uint8))
    rle = mask_util.encode(fortran_mask[:, :, np.newaxis])[0]
    # Convert bytes to str for JSON/JSONB storage
    rle["counts"] = rle["counts"].decode("utf-8")
    return rle


def _merge_boundary_masks(
    database_session,
    observation_uuid: uuid.UUID,
    iou_threshold: float,
) -> tuple[int, list[uuid.UUID]]:
    """Merge masks for duplicate objects in overlapping sub-region zones.

    After all sub-region detections are complete, finds candidate pairs of
    objects from different detection scale levels whose bounding boxes overlap.
    Computes IoU between their RLE-encoded masks. If IoU >= threshold, keeps
    the detection with higher SNR and deletes the other.

    Only considers pairs where both objects have segmentation masks (i.e.,
    segmentation_mask_rle is not None).

    Args:
        database_session: SQLAlchemy session.
        observation_uuid: UUID of the observation.
        iou_threshold: Minimum IoU to consider two detections as duplicates.

    Returns:
        Tuple of (merged_pair_count, list_of_deleted_uuids).
    """
    # Query all objects with masks for this observation
    objects_with_masks = (
        database_session.query(AstronomicalObject)
        .filter(
            AstronomicalObject.source_observation_uuid == observation_uuid,
            AstronomicalObject.segmentation_mask_rle.isnot(None),
        )
        .all()
    )

    if len(objects_with_masks) < 2:
        return 0, []

    # Build spatial index from bounding boxes for fast overlap checking
    deleted_uuids = set()
    merged_count = 0

    # Group by scale level to compare across scales (not within same scale)
    scale_groups = {}
    for obj in objects_with_masks:
        scale = obj.detection_scale_level or "unknown"
        if scale not in scale_groups:
            scale_groups[scale] = []
        scale_groups[scale].append(obj)

    scale_levels = list(scale_groups.keys())

    for i in range(len(scale_levels)):
        for j in range(i + 1, len(scale_levels)):
            group_a = scale_groups[scale_levels[i]]
            group_b = scale_groups[scale_levels[j]]

            for obj_a in group_a:
                if obj_a.object_uuid in deleted_uuids:
                    continue
                bbox_a = obj_a.bounding_box_pixels
                if not bbox_a:
                    continue

                for obj_b in group_b:
                    if obj_b.object_uuid in deleted_uuids:
                        continue
                    bbox_b = obj_b.bounding_box_pixels
                    if not bbox_b:
                        continue

                    # Quick bounding box overlap check
                    if (
                        bbox_a["xmax"] <= bbox_b["xmin"]
                        or bbox_b["xmax"] <= bbox_a["xmin"]
                        or bbox_a["ymax"] <= bbox_b["ymin"]
                        or bbox_b["ymax"] <= bbox_a["ymin"]
                    ):
                        continue

                    # Compute IoU from RLE masks
                    rle_a = obj_a.segmentation_mask_rle
                    rle_b = obj_b.segmentation_mask_rle

                    if not rle_a or not rle_b:
                        continue

                    # Ensure counts are bytes for pycocotools
                    rle_a_copy = dict(rle_a)
                    rle_b_copy = dict(rle_b)
                    if isinstance(rle_a_copy["counts"], str):
                        rle_a_copy["counts"] = rle_a_copy["counts"].encode(
                            "utf-8"
                        )
                    if isinstance(rle_b_copy["counts"], str):
                        rle_b_copy["counts"] = rle_b_copy["counts"].encode(
                            "utf-8"
                        )

                    # Masks must have same size for IoU comparison
                    if rle_a_copy.get("size") != rle_b_copy.get("size"):
                        continue

                    try:
                        iou_matrix = mask_util.iou(
                            [rle_a_copy], [rle_b_copy], [False]
                        )
                        iou_value = float(iou_matrix[0][0])
                    except Exception:
                        continue

                    if iou_value >= iou_threshold:
                        # Keep the one with higher SNR, delete the other
                        snr_a = obj_a.detection_signal_to_noise_ratio or 0.0
                        snr_b = obj_b.detection_signal_to_noise_ratio or 0.0

                        if snr_a >= snr_b:
                            to_delete = obj_b
                        else:
                            to_delete = obj_a

                        deleted_uuids.add(to_delete.object_uuid)
                        database_session.delete(to_delete)
                        merged_count += 1

                        logger.debug(
                            "Merged duplicate: deleted %s (SNR=%.1f) in "
                            "favor of %s (SNR=%.1f), IoU=%.3f",
                            to_delete.object_uuid,
                            to_delete.detection_signal_to_noise_ratio or 0,
                            (
                                obj_a.object_uuid
                                if to_delete == obj_b
                                else obj_b.object_uuid
                            ),
                            max(snr_a, snr_b),
                            iou_value,
                        )

    if merged_count > 0:
        database_session.flush()

    logger.info(
        "Boundary merging complete: %d duplicates removed from %d objects",
        merged_count,
        len(objects_with_masks),
    )

    return merged_count, list(deleted_uuids)


def _compute_normalization_parameters(
    fits_data: np.ndarray,
) -> tuple[float, float]:
    """Compute ZScale normalization parameters from a subsample of the image.

    Same approach as tile.py -- samples approximately 100 rows to compute
    ZScale limits without loading the full image.

    Args:
        fits_data: 2D float32 FITS data array.

    Returns:
        Tuple of (vmin, vmax).
    """
    ny, nx = fits_data.shape
    step = max(1, ny // 100)
    sample = np.array(fits_data[::step, ::step], dtype=np.float32)
    sample = np.nan_to_num(sample, nan=0.0, posinf=0.0, neginf=0.0)

    interval = ZScaleInterval()
    vmin, vmax = interval.get_limits(sample)

    return float(vmin), float(vmax)


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def segment_sam(self, detection_result: dict) -> dict:
    """Generate segmentation masks for all detected astronomical objects.

    Attempts SAM 3 (CUDA GPU) for pixel-level masks. Falls back to SEP
    elliptical aperture masks when CUDA is unavailable. All masks are
    encoded as COCO RLE and stored in AstronomicalObject.segmentation_mask_rle.
    After masking, runs boundary merging to deduplicate objects in overlapping
    sub-region zones.

    Data flow:
        detection_result["observation_uuid"] -> observation UUID
        detection_result["fits_s3_keys"] -> FITS download for image data
        detection_result["source_count"] -> early exit if 0
        detection_result["object_uuids"] -> objects to segment

    Args:
        detection_result: Dict from detect_sources.

    Returns:
        Dict with observation_uuid, fits_s3_keys, object_uuids (remaining
        after merge), has_sam_masks flag, and masks_generated count.
    """
    observation_uuid_hex = detection_result["observation_uuid"]
    observation_uuid = uuid.UUID(observation_uuid_hex)
    fits_s3_keys = detection_result.get("fits_s3_keys", [])
    source_count = detection_result.get("source_count", 0)

    database_session = SessionLocal()
    processing_step = None
    temp_fits_path = None

    try:
        # Create ProcessingStep record
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="segment_sam",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        # Early exit if no sources detected
        if source_count == 0:
            processing_step.step_status = StepStatus.completed
            processing_step.step_completed_at = sql_func.now()
            processing_step.step_output_metadata = {
                "masks_generated": 0,
                "method": "none",
                "reason": "no sources detected",
            }
            database_session.commit()

            logger.info(
                "No sources to segment for observation %s",
                observation_uuid_hex,
            )

            return {
                "observation_uuid": observation_uuid_hex,
                "fits_s3_keys": fits_s3_keys,
                "object_uuids": [],
                "has_sam_masks": False,
                "masks_generated": 0,
            }

        logger.info(
            "Starting segmentation for observation %s (%d sources)",
            observation_uuid_hex,
            source_count,
        )

        # Download FITS for image data
        s3_client = get_s3_client()
        temp_fd, temp_fits_path = tempfile.mkstemp(suffix=".fits")
        os.close(temp_fd)

        s3_client.download_file(
            settings.s3_bucket_fits_raw,
            fits_s3_keys[0],
            temp_fits_path,
        )

        # Open FITS and get 2D data
        with fits.open(temp_fits_path, memmap=True, mode="denywrite") as hdul:
            sci_hdu = _find_sci_extension(hdul)
            fits_data = sci_hdu.data

            # Handle 3D+ cubes
            if fits_data.ndim > 2:
                while fits_data.ndim > 2:
                    fits_data = fits_data[0]

            fits_data = np.array(fits_data, dtype=np.float32)

            # Fix byte order
            if fits_data.dtype.byteorder not in ("=", "<", "|"):
                fits_data = fits_data.byteswap().newbyteorder()

        image_height, image_width = fits_data.shape

        # Compute normalization parameters for SAM RGB conversion
        vmin, vmax = _compute_normalization_parameters(fits_data)

        # Attempt SAM initialization
        processor = _get_sam_processor()
        method = "sam3" if processor is not None else "sep_ellipse"

        logger.info(
            "Segmentation method: %s for observation %s",
            method,
            observation_uuid_hex,
        )

        # Query all AstronomicalObject records for this observation
        all_objects = (
            database_session.query(AstronomicalObject)
            .filter(
                AstronomicalObject.source_observation_uuid == observation_uuid
            )
            .all()
        )

        masks_generated = 0

        for astro_object in all_objects:
            physical_props = astro_object.physical_properties or {}
            sep_a = physical_props.get("sep_a", 1.0)
            sep_b = physical_props.get("sep_b", 1.0)
            sep_theta = physical_props.get("sep_theta", 0.0)

            bbox = astro_object.bounding_box_pixels or {}
            pixel_x = astro_object.pixel_centroid_x
            pixel_y = astro_object.pixel_centroid_y

            if pixel_x is None or pixel_y is None:
                continue

            binary_mask = None
            used_method = method

            # Determine if we can use SAM for this object
            use_sam_for_this = False
            if method == "sam3" and processor is not None:
                scale_level = astro_object.detection_scale_level
                if scale_level == "full_field":
                    # SAM can't handle >1024px; use elliptical for large images
                    if (
                        image_height <= SAM_MAX_IMAGE_DIMENSION
                        and image_width <= SAM_MAX_IMAGE_DIMENSION
                    ):
                        use_sam_for_this = True
                    else:
                        used_method = "sep_ellipse"
                        logger.debug(
                            "Full-field detection on %dx%d image -- "
                            "using SEP elliptical mask (SAM max=%dpx)",
                            image_width,
                            image_height,
                            SAM_MAX_IMAGE_DIMENSION,
                        )
                else:
                    # Sub-region detections are <= 1024px
                    use_sam_for_this = True

            if use_sam_for_this:
                # Determine the sub-region to extract for SAM
                # Use bounding box expanded to region context
                xmin = max(0, int(bbox.get("xmin", pixel_x - 50)))
                ymin = max(0, int(bbox.get("ymin", pixel_y - 50)))
                xmax = min(
                    image_width, int(bbox.get("xmax", pixel_x + 50))
                )
                ymax = min(
                    image_height, int(bbox.get("ymax", pixel_y + 50))
                )

                # Add context padding (50% on each side)
                pad_x = max(int((xmax - xmin) * 0.5), 50)
                pad_y = max(int((ymax - ymin) * 0.5), 50)
                region_xmin = max(0, xmin - pad_x)
                region_ymin = max(0, ymin - pad_y)
                region_xmax = min(image_width, xmax + pad_x)
                region_ymax = min(image_height, ymax + pad_y)

                # Ensure region is within SAM size limits
                if (
                    region_ymax - region_ymin > SAM_MAX_IMAGE_DIMENSION
                    or region_xmax - region_xmin > SAM_MAX_IMAGE_DIMENSION
                ):
                    used_method = "sep_ellipse"
                else:
                    sub_region_data = fits_data[
                        region_ymin:region_ymax, region_xmin:region_xmax
                    ]
                    sub_region_rgb = _fits_to_sam_rgb(sub_region_data, vmin, vmax)

                    # Local coordinates within the sub-region
                    local_cx = pixel_x - region_xmin
                    local_cy = pixel_y - region_ymin
                    local_bbox = {
                        "xmin": xmin - region_xmin,
                        "ymin": ymin - region_ymin,
                        "xmax": xmax - region_xmin,
                        "ymax": ymax - region_ymin,
                    }

                    detection_prompt = {
                        "centroid_x": local_cx,
                        "centroid_y": local_cy,
                        "bbox": local_bbox,
                    }

                    sam_masks = _generate_sam_masks(
                        processor, sub_region_rgb, [detection_prompt]
                    )

                    if sam_masks and sam_masks[0] is not None:
                        local_mask = sam_masks[0]
                        # Embed local mask into full-image-sized mask
                        full_mask = np.zeros(
                            (image_height, image_width), dtype=bool
                        )
                        full_mask[
                            region_ymin:region_ymax,
                            region_xmin:region_xmax,
                        ] = local_mask[
                            : region_ymax - region_ymin,
                            : region_xmax - region_xmin,
                        ]
                        binary_mask = full_mask
                        used_method = "sam3"
                    else:
                        # SAM failed for this detection, fall back
                        used_method = "sep_ellipse"

            # SEP elliptical mask fallback
            if binary_mask is None:
                binary_mask = _generate_elliptical_mask(
                    (image_height, image_width),
                    pixel_x,
                    pixel_y,
                    sep_a,
                    sep_b,
                    sep_theta,
                )
                used_method = "sep_ellipse"

            # Ensure mask has any True pixels
            if not binary_mask.any():
                # Minimum 1-pixel mask at centroid
                cy = int(np.clip(pixel_y, 0, image_height - 1))
                cx = int(np.clip(pixel_x, 0, image_width - 1))
                binary_mask[cy, cx] = True

            # Encode to COCO RLE
            rle = _encode_mask_to_rle(binary_mask)

            # Update database record
            astro_object.segmentation_mask_rle = rle
            astro_object.segmentation_method = used_method
            masks_generated += 1

        # Flush all mask updates before merging
        database_session.flush()

        # Run boundary mask merging
        merged_count, deleted_uuids = _merge_boundary_masks(
            database_session,
            observation_uuid,
            settings.segmentation_boundary_iou_threshold,
        )

        # Compute remaining object UUIDs
        deleted_uuid_set = set(deleted_uuids)
        remaining_uuids = [
            str(obj.object_uuid)
            for obj in all_objects
            if obj.object_uuid not in deleted_uuid_set
        ]

        # Update ProcessingStep to completed
        step_output_metadata = {
            "masks_generated": masks_generated,
            "method": method,
            "merged_count": merged_count,
            "deleted_duplicates": len(deleted_uuids),
        }
        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = step_output_metadata
        database_session.commit()

        logger.info(
            "Segmentation completed for observation %s: %d masks generated "
            "(%s), %d duplicates merged, %d objects remaining",
            observation_uuid_hex,
            masks_generated,
            method,
            merged_count,
            len(remaining_uuids),
        )

        return {
            "observation_uuid": observation_uuid_hex,
            "fits_s3_keys": fits_s3_keys,
            "object_uuids": remaining_uuids,
            "has_sam_masks": method == "sam3",
            "masks_generated": masks_generated,
        }

    except Exception as exception:
        logger.exception(
            "Segmentation failed for observation %s: %s",
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
