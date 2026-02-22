---
phase: 03-sky-viewer
plan: 01
subsystem: api
tags: [fastapi, astropy, wcs, fits, minio, s3, typescript, openseadragon]

# Dependency graph
requires:
  - phase: 02-data-ingestion-tiling
    provides: "DZI tiles in MinIO tiles bucket, FITS files in fits-raw bucket, Observation + ProcessingStep DB records"
provides:
  - "Tile proxy endpoint streaming JPEGs from MinIO with immutable cache headers"
  - "WCS parameter extraction endpoint (CRPIX/CRVAL/CD matrix from FITS via astropy)"
  - "Observation detail endpoint with provenance + tile metadata"
  - "TypeScript interfaces (WcsParams, TileMetadata, ObservationDetail)"
  - "API client functions (fetchObservation, fetchWcsParams, getTileUrl)"
affects: [03-02-PLAN, 03-03-PLAN]

# Tech tracking
tech-stack:
  added: [botocore.exceptions.ClientError, astropy.wcs.WCS, astropy.io.fits]
  patterns: [tile-proxy-with-immutable-cache, wcs-extraction-from-fits-on-demand, pydantic-response-models-for-typed-api]

key-files:
  created:
    - api/routers/tiles.py
    - web/src/types/observation.ts
    - web/src/lib/api.ts
  modified:
    - api/main.py

key-decisions:
  - "WCS extracted on-demand from FITS in MinIO rather than persisted in DB -- cleaner separation, avoids modifying Phase 2 code"
  - "CD matrix falls back to CDELT1/CDELT2 for older FITS files lacking CD keywords"
  - "Tile proxy uses StreamingResponse (not download-then-send) for minimal memory usage"
  - "API client uses standard fetch() -- no axios or other HTTP library dependency"

patterns-established:
  - "Tile proxy pattern: FastAPI StreamingResponse from S3 get_object with immutable cache headers"
  - "WCS extraction pattern: download FITS to temp file, open with astropy memmap, extract via WCS.to_header(), clean up in finally block"
  - "SCI extension finder reused from pipeline/tasks/tile.py (SCI -> primary HDU -> scan all extensions)"

requirements-completed: [BROWSE-01, BROWSE-02]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 3 Plan 01: Tile Serving API & Frontend Types Summary

**FastAPI tile proxy with immutable cache headers, WCS parameter extraction from FITS via astropy, and TypeScript API client for frontend consumption**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T22:39:32Z
- **Completed:** 2026-02-22T22:41:41Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Three FastAPI endpoints: tile proxy (streaming JPEG from MinIO), WCS extraction (FITS header to JSON), observation detail (provenance + tile metadata)
- Pydantic response models ensuring typed API contract: `WcsParamsResponse`, `TileMetadataResponse`, `ObservationDetailResponse`
- TypeScript interfaces matching backend schemas: `WcsParams`, `TileMetadata`, `ObservationDetail`
- API client with `fetchObservation()`, `fetchWcsParams()`, `getTileUrl()` ready for OpenSeadragon integration in Plan 02

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tile serving API router with tile proxy, WCS extraction, and observation detail endpoints** - `ed7fc1b` (feat)
2. **Task 2: Create TypeScript interfaces and API client for observation data and WCS parameters** - `b87c442` (feat)

## Files Created/Modified

- `api/routers/tiles.py` -- FastAPI router with `APIRouter(prefix="/api/tiles")`, 3 endpoints, 3 Pydantic response models, `_find_sci_extension()` helper. Imports: `get_s3_client()` from `shared/s3`, `Observation`/`ProcessingStep`/`StepStatus` from `shared/models`, `get_database_session` from `api/db/session`, `astropy.io.fits`/`astropy.wcs.WCS` for FITS header extraction, `botocore.exceptions.ClientError` for S3 error handling.
- `api/main.py` -- Added `from api.routers.tiles import router as tiles_router` and `app.include_router(tiles_router)` registration.
- `web/src/types/observation.ts` -- Exports `WcsParams` (12 fields: crpix1/2, crval1/2, cd1_1/1_2/2_1/2_2, ctype1/2, naxis1/2), `TileMetadata` (10 fields matching `step_output_metadata` from `generate_tiles`), `ObservationDetail` (11 fields including nested `tile_metadata`).
- `web/src/lib/api.ts` -- Exports `fetchObservation(uuid)` -> `GET /api/tiles/{uuid}`, `fetchWcsParams(uuid)` -> `GET /api/tiles/{uuid}/wcs`, `getTileUrl(uuid)` -> base URL string for OpenSeadragon DZI tile source. Uses `NEXT_PUBLIC_API_URL` env var with fallback to `http://localhost:8000`.

## Architecture & Data Flow

**Call graph:**
```
Browser                         FastAPI (api/routers/tiles.py)         MinIO
  |                                                                      |
  |-- GET /api/tiles/{uuid}/{level}/{col}_{row}.jpg ---> get_tile() ---> s3.get_object(tiles bucket)
  |                                                       |              |
  |<-------- StreamingResponse(image/jpeg) <-- response["Body"] <--------+
  |
  |-- GET /api/tiles/{uuid}/wcs -----------------------> get_wcs_params()
  |                                                       |
  |                                                       +---> s3.list_objects_v2(fits-raw, MaxKeys=1)
  |                                                       +---> s3.download_file -> tempfile
  |                                                       +---> fits.open(memmap=True)
  |                                                       +---> _find_sci_extension(hdul)
  |                                                       +---> WCS(header).celestial.to_header()
  |                                                       +---> extract CRPIX/CRVAL/CD/CTYPE/NAXIS
  |<-------- WcsParamsResponse (JSON) <------------------+
  |
  |-- GET /api/tiles/{uuid} ---------------------------> get_observation_detail(db)
  |                                                       |
  |                                                       +---> db.query(Observation).filter(uuid)
  |                                                       +---> db.query(ProcessingStep).filter(
  |                                                       |       step_name="generate_tiles",
  |                                                       |       step_status=completed)
  |<-------- ObservationDetailResponse (JSON) <----------+
```

**Frontend API client chain:**
```
SkyViewer component (Plan 02)
  |
  +-- fetchObservation(uuid) --> GET /api/tiles/{uuid} --> ObservationDetail
  +-- fetchWcsParams(uuid)   --> GET /api/tiles/{uuid}/wcs --> WcsParams
  +-- getTileUrl(uuid)       --> string for OpenSeadragon tileSources.Image.Url
```

## Decisions Made

- **WCS on-demand extraction:** WCS parameters are extracted from FITS files in MinIO on each `/wcs` request rather than persisted in the database. This avoids modifying Phase 2's `validate_wcs` task and keeps the backend contract self-contained. The `/wcs` endpoint is called once per viewer session so the overhead is negligible.
- **CD matrix CDELT fallback:** The WCS endpoint checks for `CD1_1`/`CD2_2` first, falls back to `CDELT1`/`CDELT2` for older FITS files that use the CDELT convention instead of the CD matrix. Off-diagonal elements (`CD1_2`, `CD2_1`) default to 0 when absent, which is correct for images without rotation.
- **Pydantic response models:** Used Pydantic `BaseModel` subclasses for the WCS and observation detail endpoints (not the tile proxy which returns raw bytes). This provides automatic JSON schema documentation in `/docs` and type safety.
- **Standard fetch() in API client:** No axios or other HTTP library needed. The API client uses browser-native `fetch()` and propagates error `detail` from FastAPI's HTTPException responses.

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness
- All 3 API endpoints are ready for the OpenSeadragon sky viewer (Plan 02)
- TypeScript types and API client are ready for import in viewer components
- Tile URL pattern matches Phase 2's MinIO key structure exactly: `{uuid}/tiles/{level}/{col}_{row}.jpg`
- WCS extraction follows the same SCI extension finder logic as `pipeline/tasks/tile.py`

## Self-Check: PASSED

- [x] api/routers/tiles.py exists
- [x] web/src/types/observation.ts exists
- [x] web/src/lib/api.ts exists
- [x] 03-01-SUMMARY.md exists
- [x] Commit ed7fc1b found (Task 1)
- [x] Commit b87c442 found (Task 2)

---
*Phase: 03-sky-viewer*
*Completed: 2026-02-22*
