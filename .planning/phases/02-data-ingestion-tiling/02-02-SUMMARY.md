---
phase: 02-data-ingestion-tiling
plan: 02
subsystem: pipeline
tags: [wcs, astropy, pyvips, dzi, fits, celery, tiling, normalization, zscale, asinh]

# Dependency graph
requires:
  - phase: 02-data-ingestion-tiling
    plan: 01
    provides: "S3 client singleton (shared/s3.py), MAST download task, astronomy dependencies, FITS files in MinIO"
provides:
  - "WCS validation Celery task (pipeline/tasks/validate_wcs.py)"
  - "DZI tile generation Celery task (pipeline/tasks/tile.py)"
  - "Pointing RA/Dec extraction from FITS WCS headers"
  - "Memory-safe FITS normalization with ZScale + asinh stretch"
  - "DZI tile pyramids in MinIO tiles bucket for sky viewer consumption"
affects: [02-03-PLAN, 03-sky-viewer, 04-segmentation]

# Tech tracking
tech-stack:
  added: []
  patterns: [chunked-fits-processing, zscale-asinh-normalization, dzi-tile-pyramid, sci-extension-fallback]

key-files:
  created:
    - pipeline/tasks/validate_wcs.py
    - pipeline/tasks/tile.py
  modified:
    - pipeline/celery_app.py

key-decisions:
  - "WCS validation uses pixel-to-world round-trip test with 1.0 pixel error threshold"
  - "Normalization parameters (vmin/vmax) computed once from ~100-row subsample, applied to all chunks"
  - "DZI tiles use 256px size with 1px overlap, JPEG Q=85 compression"
  - "FITS SCI extension checked first with fallback to primary HDU for non-JWST files"
  - "Large images (>50k rows) use incremental pyvips strip joining instead of arrayjoin"

patterns-established:
  - "SCI extension lookup: try hdul['SCI'] -> hdul[0] -> scan all extensions (shared pattern for validate_wcs and tile)"
  - "Chunked FITS processing: read in CHUNK_ROWS bands with memmap=True, never load full array"
  - "Single normalization: compute ZScale vmin/vmax once from subsample, apply to all chunks for seamless tiles"
  - "DZI pipeline: FITS -> normalize chunks -> pyvips strips -> pyramidal TIFF -> dzsave -> MinIO upload"

requirements-completed: [INGEST-02, INGEST-03, INGEST-05]

# Metrics
duration: 8min
completed: 2026-02-22
---

# Phase 2 Plan 2: WCS Validation & Tile Generation Summary

**WCS coordinate extraction with round-trip validation and memory-safe DZI tile pyramid generation using ZScale + asinh stretch via pyvips streaming**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-22T05:23:39Z
- **Completed:** 2026-02-22T05:31:39Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented WCS validation Celery task that extracts sky coordinates from FITS SCI extension headers, validates via pixel-to-world round-trip test, and updates Observation records with pointing RA/Dec
- Implemented DZI tile generation Celery task with memory-safe chunked FITS normalization (ZScale + asinh stretch, params from subsample), pyvips DZI pyramid output, and MinIO upload
- Both tasks follow established ProcessingStep lifecycle pattern with full metadata recording, error handling, and status propagation
- Registered both new task modules in celery_app.py (now 4 total: test_noop, download, validate_wcs, tile)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement WCS validation Celery task** - `b6cda70` (feat)
2. **Task 2: Implement tile generation Celery task** - `f9b529a` (feat)

## Files Created/Modified
- `pipeline/tasks/validate_wcs.py` - WCS extraction from FITS SCI headers, round-trip validation, pointing RA/Dec update, FITS header provenance extraction
- `pipeline/tasks/tile.py` - Chunked FITS normalization with ZScale + asinh, DZI tile pyramid generation via pyvips, MinIO tile upload with content types
- `pipeline/celery_app.py` - Added validate_wcs and tile to Celery include list

## Decisions Made
- WCS round-trip validation threshold set to 1.0 pixel max error -- logs warning but continues if threshold exceeded (some FITS have approximate WCS)
- Normalization subsample step uses `max(1, ny // 100)` to sample ~100 rows -- balances accuracy vs memory for any image size
- DZI parameters: 256px tiles, 1px overlap, JPEG Q=85, 'dz' layout -- standard for OpenSeadragon viewers
- SCI extension lookup shared between validate_wcs and tile as a helper function -- checks named 'SCI' first (JWST MEF), falls back to primary HDU, then scans all extensions
- Intermediate TIFF uses pyramidal + tiled JPEG compression before DZI generation -- enables pyvips sequential streaming for memory efficiency
- Images >50,000 rows use incremental join instead of arrayjoin to avoid excessive pyvips operation tree depth

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed libvips system library via Homebrew**
- **Found during:** Task 2 (tile generation import verification)
- **Issue:** pyvips Python package was installed (from Plan 01) but libvips system library was not installed, causing import failure
- **Fix:** Ran `brew install vips` to install libvips 8.18.0
- **Files modified:** None (system package)
- **Verification:** `import pyvips` succeeds with DYLD_LIBRARY_PATH=/opt/homebrew/lib
- **Note:** macOS requires DYLD_LIBRARY_PATH=/opt/homebrew/lib for pyvips to find libvips at runtime. Celery worker startup scripts will need this environment variable.

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** System library installation necessary for pyvips functionality. No scope creep.

## Issues Encountered
- macOS DYLD_LIBRARY_PATH not automatically including /opt/homebrew/lib for pyvips to find libvips.42.dylib -- this is a known macOS SIP/sandbox behavior. The library loads correctly when the path is set. Celery worker scripts or .env should include `DYLD_LIBRARY_PATH=/opt/homebrew/lib`.

## User Setup Required
None beyond the previously noted `brew install vips` (now installed). Celery worker environments should have `DYLD_LIBRARY_PATH=/opt/homebrew/lib` set on macOS.

## Next Phase Readiness
- Three-step pipeline chain now complete: download_fits -> validate_wcs -> generate_tiles
- Plan 03 (orchestrator) can chain these tasks to process any JWST observation end-to-end
- WCS validation provides pointing coordinates needed for sky viewer overlay (Phase 3)
- DZI tiles in MinIO tiles bucket ready for OpenSeadragon consumption (Phase 3)
- Tile metadata (zoom levels, dimensions, DZI S3 key) recorded in ProcessingStep for API access

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 02-data-ingestion-tiling*
*Completed: 2026-02-22*
