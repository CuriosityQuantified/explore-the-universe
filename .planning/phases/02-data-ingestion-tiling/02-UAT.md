---
status: passed
phase: 02-data-ingestion-tiling
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-02-22T06:00:00Z
updated: 2026-02-22T07:35:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 9
name: Observation has pointing coordinates after WCS validation
expected: |
  After pipeline completes, the status endpoint response includes non-null
  `pointing_ra_degrees` and `pointing_dec_degrees` in the provenance object.
result: pass

## Tests

### 1. Docker services running
expected: Docker Compose services (PostgreSQL, Redis, MinIO, Neo4j) are all running and healthy. `docker compose ps` shows all containers Up/healthy.
result: pass

### 2. Dependencies install cleanly
expected: Running `uv pip install -e ".[dev]"` completes without errors. All astronomy packages (astropy, astroquery, pyvips, Pillow) install. `python -c "import astropy, astroquery, pyvips, PIL; print('OK')"` succeeds.
result: pass

### 3. FastAPI server starts with ingest routes
expected: Running `uvicorn api.main:app --port 8000` starts the server. Visiting http://localhost:8000/docs shows Swagger UI with POST /api/ingest and GET /api/ingest/{observation_uuid}/status endpoints listed.
result: pass (after fix: pyvips lazy import to prevent startup crash on macOS)

### 4. Celery worker discovers all task modules
expected: Running `celery -A pipeline.celery_app worker --loglevel=info` starts the worker. Startup log shows 5 registered tasks including `pipeline.tasks.download.download_fits`, `pipeline.tasks.validate_wcs.validate_wcs`, `pipeline.tasks.tile.generate_tiles`, `pipeline.tasks.ingest.ingest_observation`.
result: pass

### 5. POST /api/ingest returns 202 with observation UUID
expected: Sending `curl -X POST http://localhost:8000/api/ingest -H "Content-Type: application/json" -d '{"archive_observation_id": "jw05924-o015_t014_nircam_clear-f212n-sub64p"}'` returns HTTP 202 with JSON body containing `observation_uuid` (valid UUID) and `status: "pipeline_started"`.
result: pass (after fix: moved Observation creation from Celery task to API endpoint to eliminate race condition)

### 6. GET /api/ingest/{uuid}/status returns pipeline progress
expected: Using the observation_uuid from test 5, sending `curl http://localhost:8000/api/ingest/{uuid}/status` returns HTTP 200 with `pipeline_status`, `steps` array, and `provenance` object.
result: pass

### 7. Full pipeline completes end-to-end
expected: After triggering ingest, polling the status endpoint shows pipeline_status progressing through statuses and eventually reaching "completed". All 3 processing steps (download, validate_wcs, generate_tiles) show status "completed".
result: pass (observation jw05924-o015_t014_nircam_clear-f212n-sub64p completed in ~15 seconds; download ~5s, validate_wcs <1s, generate_tiles <1s)

### 8. Tiles exist in MinIO after pipeline completion
expected: After pipeline completes, checking MinIO tiles bucket shows DZI files and tile JPEG files under `{observation_uuid}/tiles/`.
result: pass (1 DZI file + 7 JPEG tiles across zoom levels 0-6 for 64x64 sub-array observation)

### 9. Observation has pointing coordinates after WCS validation
expected: After pipeline completes, the status endpoint response includes non-null `pointing_ra_degrees` and `pointing_dec_degrees` in the provenance object, confirming WCS extraction worked.
result: pass (RA=26.633115, Dec=2.700419)

## Summary

total: 9
passed: 9
issues: 3 (all fixed during UAT)
pending: 0
skipped: 0

## Gaps

### Gap 1: pyvips module-level import crashes FastAPI and Celery on macOS (FIXED)
- **Found during:** Test 3
- **Root cause:** `pipeline/tasks/tile.py` imported pyvips at module level (line 27). The import chain `api.main` -> `ingest router` -> `ingest task` -> `tile task` -> `import pyvips` -> `OSError: cannot load library 'libvips.42.dylib'` crashed both uvicorn and celery worker at startup.
- **Fix:** Replaced module-level `import pyvips` with `_get_pyvips()` lazy import helper that sets `DYLD_LIBRARY_PATH=/opt/homebrew/lib` on macOS before importing. Updated 3 call sites.
- **Files modified:** `pipeline/tasks/tile.py`

### Gap 2: Race condition in POST /api/ingest — API returned Celery task ID instead of observation UUID (FIXED)
- **Found during:** Test 5-6
- **Root cause:** `ingest_observation` Celery task created the Observation record inside the async task body. The API endpoint called `.delay()` then immediately queried DB by `archive_observation_id` — the record didn't exist yet. Fell back to returning Celery task ID as `observation_uuid`, causing GET status to return 404.
- **Fix:** Moved Observation creation from `pipeline/tasks/ingest.py` (Celery task) to `api/routers/ingest.py` (API endpoint). Observation is now created synchronously before dispatching the Celery chain. Also added duplicate detection (409 Conflict) for re-ingestion attempts.
- **Files modified:** `api/routers/ingest.py`, `pipeline/tasks/ingest.py`

### Gap 3: 3D FITS cubes caused WCS validation and tile generation to fail (FIXED)
- **Found during:** Test 7
- **Root cause:** Some JWST FITS files have 3D WCS projections (spectral cubes). `validate_wcs` called `all_pix2world()` with 2D coordinates on a 3D WCS. `generate_tiles` unpacked `data.shape` into `ny, nx` but got 3 values.
- **Fix:** In `validate_wcs.py`: extract 2D celestial sub-WCS via `full_wcs.celestial` when `naxis > 2`. In `tile.py`: collapse leading dimensions via `data[0]` when `data.ndim > 2`.
- **Files modified:** `pipeline/tasks/validate_wcs.py`, `pipeline/tasks/tile.py`

### Gap 4: Test observation ID used file-level format instead of MAST obs_id format (FIXED)
- **Found during:** Test 7
- **Root cause:** `TEST_ARCHIVE_OBSERVATION_ID` was `jw02731001001_04101_00001_nrca1` (exposure/file-level), but MAST `obs_id` field uses observation-level format like `jw02731-o001_t017_nircam_clear-f444w`. MAST query returned 0 results.
- **Fix:** Updated test constant to `jw05924-o015_t014_nircam_clear-f212n-sub64p` (small 64x64 sub-array, 2.5 MB total, ideal for fast integration tests).
- **Files modified:** `tests/test_ingest_pipeline.py`
