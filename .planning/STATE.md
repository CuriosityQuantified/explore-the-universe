# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Any astronomical image goes in, every object comes out segmented, classified, and explorable -- turning raw telescope data into a navigable, queryable encyclopedia of the universe.
**Current focus:** Phase 5: Classification & Cross-Matching

## Current Position

Phase: 5 of 8 (Classification & Cross-Matching)
Plan: 0 of 3 in current phase (0 complete)
Status: Planning
Last activity: 2026-02-23 -- Phase 4 complete (segmentation). All 3 plans executed.

Progress: [██████░░░░] 66.67%

## Performance Metrics

**Velocity:**
- Total plans completed: 10
- Average duration: ~21 min
- Total execution time: ~3h 32min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation & Infrastructure | 1 | ~3h | ~3h |
| 2. Data Ingestion & Tiling | 3 | 13min | 4min |
| 3. Sky Viewer | 3/3 | 15min | 5min |
| 4. Segmentation | 3/3 | 14min | 4.7min |

**Recent Trend:**
- Last 5 plans: Phase 3 Plan 2 (2 tasks, 2 commits), Phase 3 Plan 3 (2 tasks, 2 commits), Phase 4 Plan 1 (2 tasks, 2 commits), Phase 4 Plan 2 (2 tasks, 3 commits), Phase 4 Plan 3 (2 tasks, 1 commit)
- Trend: Execution speed consistent at 2-8min/plan. Phase 4 complete (3/3 plans done).

*Updated after each plan completion*
| Phase 03 P01 | 2min | 2 tasks | 4 files |
| Phase 03 P02 | 5min | 2 tasks | 13 files |
| Phase 03 P03 | 8min | 2 tasks | 9 files |
| Phase 04 P01 | 3min | 2 tasks | 11 files |
| Phase 04 P02 | 6min | 2 tasks | 2 files |
| Phase 04 P03 | 5min | 2 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 8-phase structure derived from 34 requirements across 6 categories
- [Roadmap]: Phases 3 and 4 can execute in parallel (both depend on Phase 2)
- [Roadmap]: INTEL-01 (anomaly detection) grouped with Classification, not Intelligence Layer, because it runs on feature vectors during classification
- [Roadmap]: INFRA-04 (pipeline dashboard) grouped with Browse phase, not Infrastructure, because it is a frontend deliverable
- [Phase 1]: Full initial schema with Alembic -- all 4 tables defined upfront to avoid structural redesign
- [Phase 1]: Infra in Docker, Python native -- FastAPI and Celery run natively with uv for fast iteration
- [Phase 1]: Single root venv with workspace -- one pyproject.toml at root, sub-packages with shared deps
- [Phase 1]: Start local MinIO, migrate to S3 later -- S3-compatible API means zero code changes
- [Phase 1]: PostgreSQL 16 (not 17) due to Docker Hub connectivity -- TODO to upgrade when resolved
- [Phase 1]: Celery uses explicit include= instead of autodiscover_tasks -- more reliable for nested task modules
- [Phase 1]: Next.js 16 uses src/ directory by default -- --src-dir=false flag not respected
- [Phase 2]: S3 client uses lazy singleton pattern in shared/s3.py (resolves Phase 1 TODO)
- [Phase 2]: MAST download uses query_criteria -> get_product_list -> filter_products chain (avoids obsid pitfall)
- [Phase 2]: Celery tasks create own SessionLocal() for DB access (not FastAPI dependency injection)
- [Phase 2]: Provenance from MAST query table, not FITS headers -- WCS extraction in Plan 02
- [Phase 2]: WCS round-trip validation uses 1.0 pixel error threshold, logs warning but continues for approximate WCS
- [Phase 2]: Normalization params (vmin/vmax) computed once from ~100-row subsample, applied to all chunks for seamless tiles
- [Phase 2]: DZI tiles use 256px, 1px overlap, JPEG Q=85, 'dz' layout (OpenSeadragon standard)
- [Phase 2]: FITS SCI extension checked first with fallback to primary HDU for non-JWST files
- [Phase 2]: Ingest task creates Observation record synchronously before dispatching Celery chain for immediate UUID availability
- [Phase 2]: API endpoint queries DB by archive_observation_id for UUID (not blocking on Celery task result)
- [Phase 2]: Status endpoint returns full provenance + processing steps with timestamps for pipeline monitoring
- [Phase 3]: WCS extracted on-demand from FITS in MinIO (not persisted in DB) -- avoids modifying Phase 2 code
- [Phase 3]: CD matrix falls back to CDELT1/CDELT2 for older FITS files lacking CD keywords
- [Phase 3]: Tile proxy uses StreamingResponse for minimal memory (no download-then-send)
- [Phase 3]: API client uses standard fetch() -- no external HTTP library dependency
- [Phase 3]: Imperative DOM mutation for coordinate display at 30fps (not React state) to avoid re-render overhead
- [Phase 3]: OSD MouseTrackerEvent extended locally (OsdMouseEvent) because @types/openseadragon lacks position/quick fields
- [Phase 3]: ViewerClient.tsx as separate client boundary -- server page.tsx fetches data, ViewerClient owns interactive state
- [Phase 3]: Scale bar picks "nice" angular values from predefined list for clean labels
- [Phase 3]: CSS filter for image adjustments applied to OSD canvas via canvas.style.filter -- avoids WebGL or per-pixel manipulation
- [Phase 3]: Gamma approximation via brightness factor pow(0.5, 1/gamma - 1) -- not true per-pixel power-law but acceptable for Phase 3
- [Phase 3]: Inverse WCS TAN deprojection (raDecToPixel) in CoordinateGrid for RA/Dec -> pixel conversion
- [Phase 3]: ViewerLoader SSR wrapper using next/dynamic with ssr: false -- prevents OSD from accessing DOM during SSR
- [Phase 3]: OSD 6.x drawer forced to 'canvas' (canvas2d) to avoid WebGL "Error creating texture" failures
- [Phase 3]: Band selector UI built with documented limitation -- Phase 2 overwrites tiles per FITS file
- [Phase 4]: Pipeline status fix -- tile.py no longer sets PipelineStatus.completed; observation stays processing for downstream segmentation tasks; final task (generate_cutouts) sets completed
- [Phase 4]: Stub task pattern -- detect_sources, segment_sam, generate_cutouts created as stubs raising NotImplementedError so chain/imports work before Plans 02/03
- [Phase 4]: torch/torchvision/sam3 excluded from pyproject.toml -- require CUDA-specific pip index URLs, optional GPU dependencies for Plan 04-02
- [Phase 4]: SEP ellipse params (a, b, theta, flux) stored in physical_properties JSONB for segment_sam elliptical fallback masks
- [Phase 4]: Boundary merging compares across scale levels only (not within same scale) -- within-scale dedup deferred to Phase 5/7
- [Phase 4]: Per-object SAM processing with sub-region context (bbox + 50% padding) -- keeps within SAM 1024px limit
- [Phase 4]: Full-field detections on images >1024px always use SEP elliptical masks (SAM max input size)
- [Phase 4]: fits_s3_keys recovered from download_fits ProcessingStep metadata when not in tile_result dict
- [Phase 4]: Per-cutout ZScale -- each cutout computes own ZScaleInterval limits rather than reusing full-image normalization for better per-object contrast
- [Phase 4]: Per-object temp file cleanup -- cutout files deleted after S3 upload before next object to prevent temp dir accumulation
- [Phase 4]: Cutout2D mode=partial with fill_value=0.0 for edge objects extending beyond image boundaries

### Pending Todos

- Upgrade postgres:16 to postgres:17 when Docker Hub connectivity is restored (TODO in docker-compose.yml)
- Switch minio-init from minio/minio to minio/mc:latest when Docker Hub connectivity is restored (TODO in docker-compose.yml)
- ~~Factor S3 client into shared dependency before Phase 2 (review recommendation I-2)~~ DONE in 02-01
- Create Neo4j driver as singleton at app startup (review recommendation I-3)

### Blockers/Concerns

- [Phase 4]: SAM performance on astronomical images is uncharted -- highest technical risk in the project
- ~~[Phase 2]: HiPS vs DZI tile format decision needs resolution during Phase 2 planning~~ RESOLVED: DZI chosen (OpenSeadragon standard, pyvips native support)
- [Phase 5]: Neo4j only supports WGS-84 spatial -- celestial coordinate queries must stay in PostgreSQL

## Session Continuity

Last session: 2026-02-23
Stopped at: Completed 04-03-PLAN.md (cutout generation + pipeline finalization). Phase 4 complete. Next: Phase 5 planning (Classification & Cross-Matching)
Resume file: None
GitHub repo: https://github.com/CuriosityQuantified/explore-the-universe
