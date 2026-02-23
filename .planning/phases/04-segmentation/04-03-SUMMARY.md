---
phase: 04-segmentation
plan: 03
subsystem: pipeline
tags: [astropy, cutout2d, celery, minio, fits, png, wcs, segmentation, pipeline-finalization]

# Dependency graph
requires:
  - phase: 04-segmentation plan 02
    provides: "detect_sources and segment_sam Celery tasks, AstronomicalObject records with segmentation_mask_rle, bounding_box_pixels, pixel centroids, and physical_properties"
  - phase: 04-segmentation plan 01
    provides: "cutout_s3_prefix column on AstronomicalObject, s3_bucket_segmentation config, 6-task Celery chain with generate_cutouts stub"
  - phase: 02-ingestion
    provides: "FITS files in MinIO, Observation/ProcessingStep models, pipeline chain pattern, SessionLocal() DB access pattern"
provides:
  - "generate_cutouts Celery task: per-object cutout extraction with Cutout2D, dual PNG (stretched + raw) + FITS with WCS, S3 upload, pipeline finalization"
  - "_extract_cutout_data: Cutout2D extraction with configurable padding (default 10%), mode=partial for edge objects"
  - "_create_stretched_png: ZScale + AsinhStretch normalization to uint8 PNG (same approach as tile.py)"
  - "_create_raw_png: 1st/99th percentile linear clipping to uint8 PNG"
  - "_create_fits_cutout: minimal FITS file with preserved Cutout2D WCS header"
  - "_upload_cutout_files: S3 upload of 3 cutout files per object with correct ContentType"
  - "Pipeline finalization: only task that sets PipelineStatus.completed on observation"
  - "Complete 6-task Celery chain verified end-to-end: download_fits -> validate_wcs -> generate_tiles -> detect_sources -> segment_sam -> generate_cutouts"
affects: [05-classification, 06-browse]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-object cutout processing: extract Cutout2D, create 3 files, upload, clean up temp files per object (no accumulation)"
    - "Batch DB flush every 100 objects via DB_FLUSH_BATCH_SIZE constant"
    - "Pipeline finalization ownership: generate_cutouts is the only task that sets PipelineStatus.completed"
    - "fits_s3_keys recovery from download_fits ProcessingStep metadata (same pattern as detect_sources)"

key-files:
  created: []
  modified:
    - "pipeline/tasks/generate_cutouts.py"

key-decisions:
  - "Per-object temp file cleanup: each object's 3 cutout files are deleted after upload before proceeding to the next object, preventing temp directory from growing unbounded with thousands of objects"
  - "Cutout2D mode=partial with fill_value=0.0 for edge objects whose bounding boxes extend beyond image boundaries -- zero-fills missing pixels rather than failing"
  - "ZScale interval computed per-cutout (not from full image) so each cutout's stretch is optimized for its own dynamic range"
  - "fits_s3_keys recovery from download_fits ProcessingStep metadata when not in segmentation_result dict (same defensive pattern as detect_sources)"

patterns-established:
  - "Cutout file naming convention: cutout_stretched.png, cutout_raw.png, cutout.fits per object"
  - "S3 cutout key structure: {observation_uuid}/{object_uuid}/{filename} in segmentation bucket"
  - "Pipeline finalization: final chain task sets PipelineStatus.completed and creates terminal ProcessingStep"

requirements-completed: [SEG-03]

# Metrics
duration: 5min
completed: 2026-02-23
---

# Phase 4 Plan 03: Cutout Generation & Pipeline Finalization Summary

**Per-object cutout extraction using Cutout2D with 10% padding, dual PNG (ZScale+asinh stretched + percentile-clipped raw) + WCS-preserved FITS, uploaded to MinIO segmentation bucket, with pipeline finalization setting PipelineStatus.completed**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-23T05:55:22Z
- **Completed:** 2026-02-23T06:00:22Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `generate_cutouts` Celery task (585 lines, 7 functions) replaces the stub as the final link in the 6-task pipeline chain. For each `AstronomicalObject`, it extracts a `Cutout2D` with 10% padding (`_extract_cutout_data`), generates 3 files (`_create_stretched_png`, `_create_raw_png`, `_create_fits_cutout`), uploads them to MinIO (`_upload_cutout_files`), updates `cutout_s3_prefix` in PostgreSQL, and sets `Observation.pipeline_status = PipelineStatus.completed`
- End-to-end pipeline verified: all 6 processing steps (download_fits, validate_wcs, generate_tiles, detect_sources, segment_sam, generate_cutouts) import cleanly, register with Celery (8 total registrations), and chain correctly
- Verification confirmed: SEP detection on synthetic data (5/5 sources), Kron photometry + confidence tiers, COCO RLE encode/decode roundtrip, Cutout2D with WCS preservation, dual PNG generation, SAM graceful CPU fallback, PipelineStatus.completed only in generate_cutouts (not tile.py)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement cutout generation and pipeline finalization task** - `c1c187d` (feat)
2. **Task 2: Verify end-to-end segmentation pipeline** - checkpoint:human-verify (approved)

## Files Created/Modified

- `pipeline/tasks/generate_cutouts.py` - Full implementation replacing stub. 7 functions: `_find_sci_extension(hdul)` (FITS SCI HDU lookup, same pattern as detect_sources/tile.py), `_extract_cutout_data(fits_data, wcs_object, centroid_x, centroid_y, bbox, padding_fraction=0.1) -> Cutout2D` (padded bounding box extraction with 16px minimum, mode=partial for edge objects), `_create_stretched_png(cutout_data, output_path)` (ZScaleInterval + AsinhStretch(a=0.1) normalization to uint8 grayscale PNG via PIL), `_create_raw_png(cutout_data, output_path)` (1st/99th percentile linear clipping to uint8 PNG), `_create_fits_cutout(cutout_2d, output_path)` (PrimaryHDU with Cutout2D.wcs.to_header()), `_upload_cutout_files(s3_client, obs_uuid_hex, obj_uuid_hex, temp_dir) -> (s3_prefix, bytes)` (3-file upload to segmentation bucket with ContentType headers), `generate_cutouts(self, segmentation_result) -> dict` (Celery task: ProcessingStep creation, FITS download, per-object cutout loop with DB batch flush every 100, PipelineStatus.completed finalization, exception handling with failed status marking). 585 lines total.

## Decisions Made

- **Per-cutout ZScale:** Each cutout computes its own ZScaleInterval limits rather than reusing the full-image normalization. This produces better contrast for individual objects whose dynamic range may differ significantly from the full field.
- **Per-object temp cleanup:** Cutout files for each object are deleted after S3 upload before processing the next object. This prevents the temp directory from growing unbounded when processing thousands of objects.
- **Cutout2D mode=partial:** Edge objects whose padded bounding boxes extend beyond the image boundary get zero-filled pixels rather than causing failures. This matches the plan specification exactly.
- **fits_s3_keys defensive recovery:** Same pattern as detect_sources -- recovers fits_s3_keys from download_fits ProcessingStep metadata if not present in the input dict, handling the case where upstream tasks don't pass them through.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required. The generate_cutouts task uses the existing MinIO segmentation bucket (created by docker-compose minio-init) and existing database schema (cutout_s3_prefix column added in Plan 04-01 migration).

## Next Phase Readiness

- Phase 4 (Segmentation) is fully complete: all 3 plans executed, all 4 SEG requirements met
- Phase 5 (Classification & Cross-Matching) can begin: AstronomicalObject records have sky coordinates (RA/Dec), confidence tiers, segmentation masks, cutout images, and physical properties -- all inputs needed for catalog cross-matching
- The complete 6-task Celery chain works end-to-end on JWST observations
- CPU-only environments produce valid results via SEP elliptical mask fallback (SAM 3 is optional for CUDA systems)

## Self-Check: PASSED

All 1 modified file verified present. Task 1 commit (c1c187d) verified in git log.

---
*Phase: 04-segmentation*
*Completed: 2026-02-23*
