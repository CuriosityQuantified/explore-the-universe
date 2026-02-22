---
phase: 02-data-ingestion-tiling
plan: 01
subsystem: pipeline
tags: [mast, astroquery, celery, s3, minio, fits, jwst, boto3]

# Dependency graph
requires:
  - phase: 01-foundation-infrastructure
    provides: "PostgreSQL schema (Observation, ProcessingStep), Celery app, MinIO buckets, shared config"
provides:
  - "Reusable S3 client singleton (shared/s3.py)"
  - "MAST download Celery task (pipeline/tasks/download.py)"
  - "Astronomy dependency stack (astropy, astroquery, pyvips, Pillow)"
  - "MAST configuration settings in shared/config.py"
affects: [02-02-PLAN, 02-03-PLAN, 03-segmentation]

# Tech tracking
tech-stack:
  added: [astropy, astroquery, pyvips, Pillow, numpy, pyerfa, pyvo, beautifulsoup4]
  patterns: [lazy-singleton, celery-task-with-db-session, mast-query-then-filter]

key-files:
  created:
    - shared/s3.py
    - pipeline/tasks/download.py
  modified:
    - shared/config.py
    - pyproject.toml
    - pipeline/celery_app.py

key-decisions:
  - "S3 client uses lazy singleton pattern with module-level _s3_client variable"
  - "MAST download uses query_criteria() -> get_product_list() -> filter_products() chain to avoid obsid/obs_id pitfall"
  - "Celery task creates its own SQLAlchemy session (SessionLocal) instead of FastAPI dependency injection"
  - "Provenance extracted from MAST query table (not FITS headers) -- WCS extraction deferred to Plan 02"

patterns-established:
  - "Lazy singleton: module-level variable initialized on first call (shared/s3.py pattern)"
  - "Celery DB session: create SessionLocal(), commit/rollback/close in try/except/finally"
  - "ProcessingStep lifecycle: create(running) -> update(completed/failed) with timestamps"
  - "MinIO key format: {observation_uuid}/{filename} in fits-raw bucket"

requirements-completed: [INGEST-01, INGEST-04]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 2 Plan 1: MAST Download Task Summary

**Shared S3 client singleton and MAST download Celery task with query-filter-download-upload pipeline for JWST calibrated FITS files**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T05:18:14Z
- **Completed:** 2026-02-22T05:20:39Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created reusable S3 client singleton (shared/s3.py) resolving Phase 1 TODO about factoring S3 client into shared dependency
- Added full astronomy dependency stack (astropy, astroquery, pyvips, Pillow) to pyproject.toml
- Implemented complete MAST download Celery task with query -> filter -> download -> MinIO upload -> provenance extraction pipeline
- Download task includes ProcessingStep lifecycle tracking, error handling with status propagation, and Celery retry with exponential backoff

## Task Commits

Each task was committed atomically:

1. **Task 1: Create shared S3 client and add astronomy dependencies** - `ed9e478` (feat)
2. **Task 2: Implement MAST download Celery task** - `d4184d9` (feat)

## Files Created/Modified
- `shared/s3.py` - Reusable boto3 S3 client singleton with lazy initialization for MinIO access
- `shared/config.py` - Added mast_api_token and mast_download_directory settings
- `pyproject.toml` - Added astropy, astroquery, pyvips, Pillow dependencies
- `pipeline/tasks/download.py` - Full MAST query -> filter -> download -> MinIO upload Celery task with provenance extraction
- `pipeline/celery_app.py` - Added pipeline.tasks.download to Celery include list

## Decisions Made
- S3 client uses lazy singleton pattern (module-level `_s3_client` initialized on first call) -- simple, thread-safe for boto3 API calls, matches Phase 1 TODO resolution
- MAST download follows query_criteria() -> get_product_list() -> filter_products() chain explicitly to avoid the obsid vs obs_id confusion pitfall identified in research
- Celery task creates its own `SessionLocal()` for database access rather than using FastAPI's `get_database_session` generator -- Celery tasks are not HTTP requests
- Provenance metadata (telescope, instrument, filters, exposure) extracted from MAST query results table, not FITS headers -- WCS validation and coordinate extraction deferred to Plan 02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. The astronomy dependencies (astropy, astroquery) access public MAST data without authentication. The pyvips library requires libvips system library (`brew install vips` on macOS), noted in pyproject.toml.

## Next Phase Readiness
- S3 client singleton ready for use by all subsequent pipeline tasks (WCS validation, tiling)
- Download task ready to be called by orchestrator (Plan 03) once observation records are created
- Provenance metadata fields populated; pointing_ra_degrees and pointing_dec_degrees will be filled by WCS validation in Plan 02
- MAST configuration in place for public JWST data access

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 02-data-ingestion-tiling*
*Completed: 2026-02-22*
