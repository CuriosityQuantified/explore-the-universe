---
phase: 04-segmentation
plan: 02
subsystem: pipeline
tags: [sep, pycocotools, sam3, celery, segmentation, source-detection, kron-photometry, coco-rle]

# Dependency graph
requires:
  - phase: 04-segmentation plan 01
    provides: "DetectionConfidenceTier enum, 10 segmentation columns on AstronomicalObject, 14 segmentation config settings, stub task files, extended 6-task Celery chain"
  - phase: 02-ingestion
    provides: "FITS files in MinIO, WCS headers, Observation/ProcessingStep models, pipeline chain pattern"
provides:
  - "detect_sources Celery task: multi-scale SEP source detection at 3 scales (full field, 1024px sub-regions, 256px sub-sub-regions) with 20% overlap"
  - "segment_sam Celery task: SAM 3 pixel-level masks (CUDA) or SEP elliptical aperture masks (CPU fallback), COCO RLE encoding, boundary IoU merging"
  - "_fix_byte_order: numpy 2.x compatible FITS big-endian to native byte order conversion"
  - "_detect_sources_in_array: SEP background estimation + source extraction pipeline"
  - "_compute_kron_photometry: Kron radius photometry for SNR-based confidence tiers"
  - "_assign_confidence_tiers: SNR threshold mapping to high/medium/low DetectionConfidenceTier"
  - "_flag_edge_detections: boundary proximity check within 5px of sub-region and image edges"
  - "_extract_sub_regions: overlapping tile coordinate generation for multi-scale processing"
  - "_generate_elliptical_mask: SEP a/b/theta to binary mask with ELLIPSE_MASK_KRON_FACTOR=3.0 scaling"
  - "_encode_mask_to_rle: COCO RLE encoding via pycocotools with Fortran-order handling"
  - "_merge_boundary_masks: cross-scale IoU-based duplicate removal keeping higher-SNR detection"
  - "_fits_to_sam_rgb: ZScale + asinh stretch float32-to-uint8 RGB conversion for SAM input"
  - "_get_sam_processor: lazy SAM 3 singleton with CUDA check and graceful fallback"
affects: [04-segmentation plan 03, 05-classification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-scale detection: full field -> sub-regions (1024px) -> sub-sub-regions (256px) with 20% overlap"
    - "SEP ellipse params (a, b, theta, flux) stored in physical_properties JSONB for downstream fallback masks"
    - "COCO RLE mask encoding with Fortran-order conversion for pycocotools compatibility"
    - "SAM 3 lazy singleton with CUDA check -- graceful degradation to SEP elliptical masks without GPU"
    - "Boundary mask merging via IoU matching across detection scale levels"
    - "numpy 2.x byte order fix: use np.array(data, dtype=np.float32) instead of deprecated ndarray.newbyteorder()"

key-files:
  created: []
  modified:
    - "pipeline/tasks/detect_sources.py"
    - "pipeline/tasks/segment_sam.py"

key-decisions:
  - "SEP ellipse params (a, b, theta, flux) stored in AstronomicalObject.physical_properties JSONB so segment_sam can generate fallback masks without re-running detection"
  - "Boundary merging compares across scale levels (not within same scale) to deduplicate objects that appear at both full-field and sub-region scales"
  - "SAM processes each object individually with extracted sub-region context (bbox + 50% padding) rather than full-image batch processing"
  - "Full-field detections on images >1024px always use SEP elliptical masks (SAM max input is 1024px)"
  - "fits_s3_keys recovery from download_fits ProcessingStep metadata when not passed through generate_tiles return dict"

patterns-established:
  - "Multi-scale SEP detection pattern: _detect_and_store() called per-region with global coordinate offsets"
  - "SAM fallback pattern: try SAM -> on failure/unavailable use SEP elliptical mask per-object"
  - "Mask encoding pipeline: binary_mask -> np.asfortranarray -> pycocotools.mask.encode -> decode counts to str"

requirements-completed: [SEG-01, SEG-02, SEG-04]

# Metrics
duration: 6min
completed: 2026-02-23
---

# Phase 4 Plan 02: Source Detection & Segmentation Summary

**Multi-scale SEP source detection (full field + 1024px + 256px sub-regions with 20% overlap) with Kron photometry confidence tiers, and SAM 3 pixel-level segmentation with SEP elliptical aperture CPU fallback, COCO RLE mask encoding, and boundary IoU deduplication**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-23T05:45:25Z
- **Completed:** 2026-02-23T05:51:31Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `detect_sources` Celery task implements full three-scale SEP source detection pipeline: `_detect_sources_in_array()` runs `sep.Background()` + `sep.extract()`, `_compute_kron_photometry()` runs `sep.kron_radius()` + `sep.sum_ellipse()` for SNR, `_assign_confidence_tiers()` maps SNR to high (>=10)/medium (>=3)/low enum values, `_flag_edge_detections()` checks 5px boundary proximity, and `_run_multi_scale_detection()` orchestrates full field -> sub-regions -> sub-sub-regions with `_extract_sub_regions()` generating overlapping tiles
- `segment_sam` Celery task generates pixel-level masks for every detection: `_get_sam_processor()` lazily initializes SAM 3 with CUDA check (returns None on CPU), `_fits_to_sam_rgb()` converts float32 FITS data to uint8 RGB via ZScale + AsinhStretch, `_generate_sam_masks()` uses point+box prompts from SEP centroids/bboxes, `_generate_elliptical_mask()` creates binary masks from SEP a/b/theta params as CPU fallback, `_encode_mask_to_rle()` encodes all masks to COCO RLE via pycocotools
- Boundary mask merging (`_merge_boundary_masks()`) compares objects across different detection scale levels using `pycocotools.mask.iou()` on stored RLE masks, deleting the lower-SNR duplicate when IoU >= 0.5
- SEP ellipse parameters (a, b, theta, flux) stored in `AstronomicalObject.physical_properties` JSONB during detection, enabling segment_sam to generate fallback masks without re-running SEP

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement multi-scale SEP source detection task** - `0fdce8d` (feat)
2. **Task 2: Implement SAM 3 segmentation with CPU fallback and boundary merging** - `0eae25e` (feat)
3. **Auto-fix: numpy 2.x byte order compatibility** - `1b85207` (fix)

## Files Created/Modified

- `pipeline/tasks/detect_sources.py` - Full implementation replacing stub. 10 functions: `_find_sci_extension()` (FITS HDU lookup), `_fix_byte_order(data)` (big-endian -> native float32), `_detect_sources_in_array(data)` (SEP background + extract), `_compute_kron_photometry(data_sub, bkg, objects)` (Kron radius + ellipse sum), `_assign_confidence_tiers(flux, flux_error)` (SNR -> high/medium/low), `_flag_edge_detections(objects, ...)` (5px boundary check), `_extract_sub_regions(h, w, size, overlap)` (overlapping tile coords), `_run_multi_scale_detection(fits_data, wcs, uuid, session)` (3-scale orchestrator), `_detect_and_store(data, wcs, ...)` (detect + AstronomicalObject batch insert), `detect_sources(self, tile_result)` (Celery task entry point). 859 lines.
- `pipeline/tasks/segment_sam.py` - Full implementation replacing stub. 10 functions: `_find_sci_extension()`, `_get_sam_processor()` (lazy SAM3 singleton), `_fits_to_sam_rgb(fits_data, vmin, vmax)` (float32 -> uint8 RGB), `_generate_sam_masks(processor, rgb, detections)` (SAM point+box prompts), `_generate_elliptical_mask(shape, cx, cy, a, b, theta)` (SEP ellipse -> binary mask), `_encode_mask_to_rle(mask)` (COCO RLE encoding), `_merge_boundary_masks(session, uuid, threshold)` (IoU dedup across scales), `_compute_normalization_parameters(fits_data)` (ZScale subsample), `segment_sam(self, detection_result)` (Celery task entry point). 865 lines.

## Decisions Made

- **SEP ellipse params in physical_properties:** detect_sources stores `{"sep_a": float, "sep_b": float, "sep_theta": float, "sep_flux": float}` in the JSONB column so segment_sam can generate elliptical fallback masks without re-running detection. This cross-task data dependency is the reason Task 2 notes "IMPORTANT: detect_sources must store SEP ellipse params."
- **Per-object SAM processing:** Rather than batch-processing all detections through SAM on the full image, each object is processed with its extracted sub-region (bounding box + 50% context padding). This keeps sub-region sizes within SAM's 1024px limit and avoids loading the full image into GPU memory.
- **Cross-scale merging only:** Boundary merging compares objects across different detection_scale_level values (full_field vs sub_region, sub_region vs sub_sub_region), not within the same scale. Within-scale deduplication is deferred to Phase 5/7 per the locked decision to "keep all detections across scales."
- **fits_s3_keys recovery:** generate_tiles does not include fits_s3_keys in its return dict, so detect_sources recovers them from the download_fits ProcessingStep metadata in the database. This avoids modifying the generate_tiles return contract.
- **Full-field SAM threshold:** Full-field detections on images larger than 1024x1024 always use SEP elliptical masks instead of SAM, because SAM's input size limit is 1024px. Sub-region detections (which are <= 1024px by definition) can use SAM when CUDA is available.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _fix_byte_order for numpy 2.x compatibility**
- **Found during:** Task 2 verification (comprehensive verification script)
- **Issue:** `ndarray.newbyteorder()` was removed in numpy 2.x (installed: numpy 2.4.2). The original code `data.byteswap().newbyteorder()` raised `AttributeError: 'numpy.ndarray' object has no attribute 'newbyteorder'`.
- **Fix:** Replaced with `np.array(data, dtype=np.float32)` which handles byte-order conversion automatically during the copy/cast operation. Preserved zero-copy path for already-native arrays.
- **Files modified:** `pipeline/tasks/detect_sources.py`
- **Verification:** Tested with big-endian `>f4` input and native `float32` input; both produce correct native-order float32 output.
- **Committed in:** `1b85207`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for runtime correctness with the installed numpy version. No scope creep.

## Issues Encountered

None beyond the byte-order compatibility issue (documented as deviation above).

## User Setup Required

None - no external service configuration required. SAM 3 (GPU path) is optional and only activates when torch+CUDA is available. The SEP elliptical fallback path works with all installed dependencies.

## Next Phase Readiness

- Both core segmentation tasks are fully implemented and ready for the pipeline chain
- Plan 04-03 (generate_cutouts) can now implement the final task in the chain using detection and segmentation results
- detect_sources output dict feeds directly into segment_sam input dict (Celery chain compatibility confirmed)
- segment_sam output dict provides object_uuids and fits_s3_keys for generate_cutouts
- All AstronomicalObject records have segmentation_mask_rle populated (either SAM or SEP elliptical)

## Self-Check: PASSED

All 2 modified files verified present. All 3 commits (0fdce8d, 0eae25e, 1b85207) verified in git log.

---
*Phase: 04-segmentation*
*Completed: 2026-02-23*
