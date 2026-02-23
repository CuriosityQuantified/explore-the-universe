---
phase: 04-segmentation
plan: 01
subsystem: database, pipeline, infra
tags: [sqlalchemy, alembic, celery, sep, photutils, pycocotools, segmentation, minio]

# Dependency graph
requires:
  - phase: 02-ingestion
    provides: "AstronomicalObject model, pipeline chain (download -> validate_wcs -> generate_tiles), MinIO buckets"
provides:
  - "DetectionConfidenceTier enum with high/medium/low values"
  - "10 segmentation columns on AstronomicalObject (mask RLE, cutout prefix, bounding box, SNR, confidence tier, scale level, edge flag, pixel centroids, segmentation method)"
  - "14 segmentation config settings on Settings class"
  - "Stub task files: detect_sources.py, segment_sam.py, generate_cutouts.py"
  - "Extended 6-task Celery chain: download_fits -> validate_wcs -> generate_tiles -> detect_sources -> segment_sam -> generate_cutouts"
  - "Alembic migration for segmentation columns"
  - "MinIO segmentation bucket in docker-compose"
affects: [04-segmentation plan 02, 04-segmentation plan 03]

# Tech tracking
tech-stack:
  added: ["sep>=1.4.0", "photutils>=2.3.0", "pycocotools>=2.0.11"]
  patterns: ["Celery chain extended with stub tasks for incremental implementation", "Pipeline status flow: intermediate tasks leave observation in 'processing', only final task sets 'completed'"]

key-files:
  created:
    - "pipeline/tasks/detect_sources.py"
    - "pipeline/tasks/segment_sam.py"
    - "pipeline/tasks/generate_cutouts.py"
    - "alembic/versions/2abf67c31898_add_segmentation_columns_to_.py"
  modified:
    - "shared/models.py"
    - "shared/config.py"
    - "pyproject.toml"
    - "docker-compose.yml"
    - "pipeline/celery_app.py"
    - "pipeline/tasks/ingest.py"
    - "pipeline/tasks/tile.py"

key-decisions:
  - "Pipeline status fix: tile.py no longer sets PipelineStatus.completed -- observation stays in 'processing' so downstream segmentation tasks can run; final task (generate_cutouts) will set completed"
  - "Stub task pattern: detect_sources, segment_sam, generate_cutouts created as stub files raising NotImplementedError so imports and chain work before Plans 02/03 implement them"
  - "Alembic migration adds server_default=false on is_edge_detection column so existing rows get a default value"
  - "torch/torchvision/sam3 not declared in pyproject.toml -- they require CUDA-specific pip index URLs and are only needed for SAM task in Plan 04-02"

patterns-established:
  - "Stub task pattern: create Celery task files with NotImplementedError so chain/imports work before full implementation"
  - "Pipeline status ownership: only the final task in the chain sets observation to completed"

requirements-completed: [SEG-01, SEG-02, SEG-03, SEG-04]

# Metrics
duration: 3min
completed: 2026-02-23
---

# Phase 4 Plan 01: Segmentation Foundation Summary

**Database schema with 10 segmentation columns, 14-field config, extended 6-task Celery chain, and sep/photutils/pycocotools dependencies for astronomical source detection pipeline**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-23T05:39:13Z
- **Completed:** 2026-02-23T05:42:05Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- AstronomicalObject model extended with 10 segmentation columns: `segmentation_mask_rle` (JSONB, COCO RLE), `cutout_s3_prefix` (String), `bounding_box_pixels` (JSONB), `detection_signal_to_noise_ratio` (Float), `detection_confidence_tier` (Enum), `detection_scale_level` (String), `is_edge_detection` (Boolean), `pixel_centroid_x` (Float), `pixel_centroid_y` (Float), `segmentation_method` (String)
- Pipeline chain extended from 3 tasks to 6 tasks with stub implementations for detect_sources, segment_sam, and generate_cutouts
- Critical pipeline status fix: tile generation no longer prematurely marks observation as completed, allowing downstream segmentation tasks to run
- Settings class extended with 14 segmentation config fields covering S3 bucket, SAM model paths, detection thresholds, multi-scale parameters, SNR confidence tiers, cutout padding, and boundary IoU

## Task Commits

Each task was committed atomically:

1. **Task 1: Add segmentation schema, config, and dependencies** - `cc8650b` (feat)
2. **Task 2: Fix pipeline status flow and extend Celery chain** - `b5b1a6c` (feat)

## Files Created/Modified

- `shared/models.py` - Added `DetectionConfidenceTier(str, enum.Enum)` with high/medium/low values; added 10 segmentation columns to `AstronomicalObject` between `is_anomaly_flagged` and `detected_at`
- `shared/config.py` - Added 14 segmentation settings to `Settings` class: `s3_bucket_segmentation`, `sam3_model_checkpoint_path`, `sam3_bpe_path`, `segmentation_detection_threshold_sigma` (1.5), `segmentation_min_area_pixels` (5), `segmentation_deblend_nthresh` (32), `segmentation_deblend_contrast` (0.005), `segmentation_background_box_size` (64), `segmentation_sub_region_size` (1024), `segmentation_sub_sub_region_size` (256), `segmentation_overlap_fraction` (0.2), `segmentation_snr_high_threshold` (10.0), `segmentation_snr_medium_threshold` (3.0), `segmentation_cutout_padding_fraction` (0.1), `segmentation_boundary_iou_threshold` (0.5)
- `pyproject.toml` - Added `sep>=1.4.0`, `photutils>=2.3.0`, `pycocotools>=2.0.11` to dependencies with note about torch/sam3 being optional
- `docker-compose.yml` - Added `/usr/bin/mc mb --ignore-existing local/segmentation;` to minio-init entrypoint
- `alembic/versions/2abf67c31898_add_segmentation_columns_to_.py` - Migration adding all 10 columns with `detection_confidence_tier_enum` enum type creation and `server_default=false` on `is_edge_detection`
- `pipeline/tasks/tile.py` - Removed `PipelineStatus.completed` assignment in success path (lines 573-593 replaced with log message); updated docstring noting task does not set terminal pipeline status
- `pipeline/tasks/ingest.py` - Extended chain to 6 tasks: `download_fits.s() -> validate_wcs.s() -> generate_tiles.s() -> detect_sources.s() -> segment_sam.s() -> generate_cutouts.s()`; added imports for 3 new task modules
- `pipeline/celery_app.py` - Added `pipeline.tasks.detect_sources`, `pipeline.tasks.segment_sam`, `pipeline.tasks.generate_cutouts` to include list (8 total)
- `pipeline/tasks/detect_sources.py` - Stub: `detect_sources(self, tile_result: dict) -> dict` raising `NotImplementedError`
- `pipeline/tasks/segment_sam.py` - Stub: `segment_sam(self, detection_result: dict) -> dict` raising `NotImplementedError`
- `pipeline/tasks/generate_cutouts.py` - Stub: `generate_cutouts(self, segmentation_result: dict) -> dict` raising `NotImplementedError`

## Decisions Made

- **Pipeline status fix:** `tile.py` no longer sets `PipelineStatus.completed` on the observation. The observation stays in `processing` status so downstream segmentation tasks can run. The final task in the chain (`generate_cutouts`, Plan 04-03) will set `completed`. The failure path still sets `PipelineStatus.failed` (tile failure should still fail the observation).
- **Stub task pattern:** Created minimal task files with `@celery_app.task(bind=True, acks_late=True)` decorator and `raise NotImplementedError(...)` bodies. This ensures the Celery chain and imports work before Plans 02 and 03 implement the real logic.
- **Migration server_default:** Added `server_default=sa.text('false')` on `is_edge_detection` column in the migration so existing rows get a value (column is `nullable=False`).
- **GPU dependencies excluded:** `torch`, `torchvision`, and `sam3` are not declared in `pyproject.toml` because they require CUDA-specific pip index URLs and are only needed for the SAM task (Plan 04-02).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added server_default on is_edge_detection migration column**
- **Found during:** Task 1 (reviewing generated Alembic migration)
- **Issue:** `is_edge_detection` column is `nullable=False` but autogenerated migration lacked a `server_default`. Applying migration to a table with existing rows would fail with a NOT NULL constraint violation.
- **Fix:** Added `server_default=sa.text('false')` to the `add_column` call.
- **Files modified:** `alembic/versions/2abf67c31898_add_segmentation_columns_to_.py`
- **Verification:** Migration file reviewed, correct `server_default` present.
- **Committed in:** `cc8650b` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added enum drop to migration downgrade**
- **Found during:** Task 1 (reviewing generated Alembic migration)
- **Issue:** Autogenerated downgrade drops the `detection_confidence_tier` column but not the `detection_confidence_tier_enum` PostgreSQL type, leaving an orphaned type.
- **Fix:** Added `sa.Enum(...).drop(op.get_bind(), checkfirst=True)` after the column drop in the downgrade function.
- **Files modified:** `alembic/versions/2abf67c31898_add_segmentation_columns_to_.py`
- **Verification:** Migration file reviewed, enum drop present in downgrade.
- **Committed in:** `cc8650b` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes necessary for migration correctness. No scope creep.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required. The segmentation MinIO bucket will be created automatically at next `docker compose up`.

## Next Phase Readiness

- Schema ready for Plans 02 and 03 to write segmentation results
- Config settings available for detection threshold tuning
- Pipeline chain wired -- Plans 02 and 03 replace stub `NotImplementedError` bodies with real implementations
- Dependencies (sep, photutils, pycocotools) declared but not yet installed -- run `uv pip install -e ".[dev]"` before Plan 02 execution

## Self-Check: PASSED

All 11 source files verified present. Both task commits (cc8650b, b5b1a6c) verified in git log.

---
*Phase: 04-segmentation*
*Completed: 2026-02-23*
