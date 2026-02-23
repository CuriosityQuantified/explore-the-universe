---
status: passed
phase: 04-segmentation
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md]
started: 2026-02-23T06:30:00Z
updated: 2026-02-23T14:40:00Z
---

## Current Test

All tests complete.

## Tests

### 1. Docker services start with segmentation bucket
expected: `docker compose up -d` succeeds. MinIO minio-init creates `segmentation` bucket alongside `fits-raw` and `tiles`. `aws --endpoint-url http://localhost:9000 s3 ls` shows all 3 buckets.
result: PASS — MinIO health check confirms 3 buckets: fits-raw, segmentation, tiles.

### 2. Alembic migration applies cleanly
expected: `alembic upgrade head` applies the segmentation columns migration without error. `psql` or Python query confirms AstronomicalObject table has the 10 new columns (segmentation_mask_rle, cutout_s3_prefix, bounding_box_pixels, detection_signal_to_noise_ratio, detection_confidence_tier, detection_scale_level, is_edge_detection, pixel_centroid_x, pixel_centroid_y, segmentation_method).
result: PASS (after fix) — Migration initially failed with `type "detection_confidence_tier_enum" does not exist`. Fixed by adding explicit `sa.Enum(...).create(op.get_bind(), checkfirst=True)` before the column add. After fix, all 10 columns present.

### 3. New dependencies install successfully
expected: `uv pip install -e ".[dev]"` installs sep, photutils, and pycocotools without error. `python -c "import sep; import photutils; import pycocotools; print('OK')"` prints OK.
result: PASS — All three libraries import successfully.

### 4. Celery worker starts with all 8 tasks
expected: `celery -A pipeline.celery_app worker --loglevel=info` starts and logs registration of 8 tasks including detect_sources, segment_sam, and generate_cutouts. Worker stays running without import errors.
result: PASS — 8 tasks registered: download_fits, validate_wcs, generate_tiles, detect_sources, segment_sam, generate_cutouts, ingest_observation, test_pipeline_task. Note: worker must be restarted after Phase 4 code changes.

### 5. Full pipeline runs end-to-end on test observation
expected: POST to `/api/ingest` with a JWST observation ID triggers the full 6-task chain. All 6 processing steps (download_fits, validate_wcs, generate_tiles, detect_sources, segment_sam, generate_cutouts) complete with status "completed". Observation pipeline_status is "completed".
result: PASS (after fix) — Initial run failed because detect_sources queried `step_name == "download_fits"` instead of `"download"` when recovering fits_s3_keys from DB. Fixed the step name. After fix, all 6 steps completed for obs `jw01163002001_03102_00001_nrca3` (NIRCAM F210M, 8x8 image). Pipeline status: completed.

### 6. Sources detected with confidence tiers and sky coordinates
expected: After pipeline completes, AstronomicalObject records exist for the observation. Objects have non-null values for detection_confidence_tier (high/medium/low), detection_scale_level (full_field/sub_region/sub_sub_region), pixel_centroid_x/y, sky_coordinate_ra_degrees/dec, and detection_signal_to_noise_ratio.
result: PASS — 1 object detected: tier=high, scale=full_field, cx=3.48, cy=3.61, ra=89.912, dec=-65.817, snr=58.88.

### 7. Segmentation masks stored as valid COCO RLE
expected: AstronomicalObject records have segmentation_mask_rle populated (JSONB with 'size' and 'counts' keys). Masks can be decoded via pycocotools.mask.decode() to produce a 2D binary array with non-zero pixel count.
result: PASS — RLE has 'size' [8,8] and 'counts' keys. pycocotools.mask.decode() produces 8x8 array with 32 non-zero pixels.

### 8. Cutout files uploaded to MinIO
expected: Each detected object has 3 cutout files in MinIO segmentation bucket: cutout_stretched.png, cutout_raw.png, cutout.fits. Path structure: `segmentation/{observation_uuid}/{object_uuid}/`. AstronomicalObject.cutout_s3_prefix is populated.
result: PASS — 3 files in segmentation bucket: cutout.fits (8640B), cutout_raw.png (166B), cutout_stretched.png (154B). Path: segmentation/d1657413.../f71829ef.../

### 9. Pipeline works without CUDA (SEP fallback)
expected: On a machine without CUDA/torch, the pipeline still completes. segment_sam logs "SAM 3 initialization failed" and uses SEP elliptical masks as fallback. All objects get segmentation_mask_rle populated. segmentation_method column shows "sep_ellipse" (not "sam3").
result: PASS — torch not installed, SAM logs "SAM 3 initialization failed: No module named 'torch'", segmentation_method=sep_ellipse, masks populated via SEP elliptical fallback.

## Summary

total: 9
passed: 9
issues: 2 (fixed)
pending: 0
skipped: 0

## Gaps

### Gap 1: Alembic migration missing enum type creation (FIXED)
file: alembic/versions/2abf67c31898_add_segmentation_columns_to_.py
issue: `sa.Enum(...)` inside `op.add_column()` doesn't auto-create PostgreSQL enum type. Needed explicit `.create(op.get_bind(), checkfirst=True)`.
fix: Added `detection_confidence_tier_enum.create(op.get_bind(), checkfirst=True)` before the add_column.

### Gap 2: detect_sources queries wrong step name for fits_s3_keys recovery (FIXED)
file: pipeline/tasks/detect_sources.py:701
issue: Queried `step_name == "download_fits"` but actual step name is `"download"`.
fix: Changed to `step_name == "download"`.
