# Phase 1: Foundation & Infrastructure Design

**Date:** 2026-02-21
**Phase Goal:** All backend services are running and the pipeline framework can accept and track work
**Requirements:** INFRA-01, INFRA-02, INFRA-03

## Success Criteria

1. Docker Compose brings up PostgreSQL, Redis, MinIO, and Neo4j with a single command
2. Celery worker processes a no-op test task through the full chain (enqueue, execute, report status)
3. FastAPI health endpoint confirms all service connections are live
4. Raw file upload to MinIO succeeds and metadata record appears in PostgreSQL

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| DB schema scope | Full initial schema with Alembic | Observations, objects, processing_steps, catalog_cross_matches defined upfront to avoid structural redesign in later phases |
| Neo4j timing | Include in Docker Compose now | Container runs from day one (no schema/data until Phase 7) to surface integration issues early |
| Project scaffolding | All three packages (pipeline, api, web) | Establishes full monorepo shape immediately |
| Dev workflow | Infra in Docker, Python native | FastAPI and Celery run natively with uv for fast iteration; only databases/storage in Docker |
| Python deps | Single root venv with workspace | One pyproject.toml at root, pipeline and api as sub-packages with shared dependencies |
| Storage strategy | MinIO locally, migrate to S3 later | S3-compatible API means zero code changes when migrating; config swaps endpoint URL |

## Project Structure

```
explore-the-universe/
├── pyproject.toml              # Root workspace: shared deps (SQLAlchemy, Pydantic, Celery)
├── docker-compose.yml          # Postgres, Redis, MinIO, Neo4j
├── .env.example                # Template for local env vars
├── alembic.ini                 # Alembic config
├── alembic/                    # Migrations directory
│   └── versions/
├── pipeline/                   # Data pipeline package
│   ├── __init__.py
│   ├── celery_app.py           # Celery application factory
│   ├── tasks/                  # Task definitions
│   │   ├── __init__.py
│   │   └── test_noop.py        # No-op test task
│   └── config.py               # Pipeline-specific config (inherits base)
├── api/                        # FastAPI backend
│   ├── __init__.py
│   ├── main.py                 # FastAPI app with lifespan
│   ├── routers/
│   │   ├── __init__.py
│   │   └── health.py           # /health verifies all service connections
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py          # SQLAlchemy engine + session factory
│   │   └── models.py           # SQLAlchemy ORM models
│   └── config.py               # pydantic-settings config
├── web/                        # Next.js frontend (bare scaffold)
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── app/
│       └── page.tsx            # Placeholder landing page
├── shared/                     # Shared code between pipeline and api
│   ├── __init__.py
│   ├── config.py               # Base pydantic-settings (connection strings)
│   └── models.py               # Shared SQLAlchemy models
└── tests/
    ├── test_health.py          # FastAPI health endpoint test
    ├── test_celery.py          # Celery no-op task test
    └── test_minio.py           # MinIO upload test
```

## Docker Compose Services

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| postgres | `postgres:17` | 5432 | Metadata, spatial indexing, processing state |
| redis | `redis:7-alpine` | 6379 | Celery broker + result backend |
| minio | `minio/minio:latest` | 9000 (API), 9001 (console) | Object storage for FITS, tiles, masks |
| neo4j | `neo4j:5-community` | 7474 (HTTP), 7687 (Bolt) | Knowledge graph (container only, no schema yet) |

- Named Docker volumes for all services (data persists across restarts)
- MinIO init container/entrypoint creates `fits-raw` and `tiles` buckets on first run
- Postgres healthcheck for service readiness
- No Python services in Docker -- run natively with uv

## PostgreSQL Schema

Managed by Alembic. PostGIS extension enabled.

### `observations`

| Column | Type | Notes |
|--------|------|-------|
| observation_uuid | UUID, PK | |
| archive_observation_id | str, unique | MAST/archive identifier |
| archive_program_id | str, nullable | JWST program ID |
| telescope_name | str | "JWST", "Rubin" |
| instrument_name | str | "NIRCam", "MIRI" |
| spectral_filters | JSONB | List of filters used |
| total_exposure_seconds | float, nullable | |
| pointing_ra_degrees | float, nullable | Pointing center RA |
| pointing_dec_degrees | float, nullable | Pointing center Dec |
| pipeline_status | enum | pending, downloading, processing, completed, failed |
| ingested_at | timestamp | |
| last_updated_at | timestamp | |

### `processing_steps`

| Column | Type | Notes |
|--------|------|-------|
| step_uuid | UUID, PK | |
| observation_uuid | FK -> observations | |
| step_name | str | "download", "validate", "tile", "segment", "classify" |
| step_status | enum | pending, running, completed, failed, skipped |
| step_started_at | timestamp, nullable | |
| step_completed_at | timestamp, nullable | |
| error_message_text | text, nullable | |
| step_output_metadata | JSONB | Step-specific output data |

### `astronomical_objects`

| Column | Type | Notes |
|--------|------|-------|
| object_uuid | UUID, PK | |
| source_observation_uuid | FK -> observations | |
| sky_coordinate_ra_degrees | float | |
| sky_coordinate_dec_degrees | float | |
| classified_object_type | str, nullable | star, galaxy, nebula, unknown |
| classification_source_catalog | str, nullable | "simbad", "ned", "ml" |
| classification_confidence_score | float, nullable | |
| physical_properties | JSONB | Magnitude, size, spectral data |
| is_anomaly_flagged | bool, default false | |
| detected_at | timestamp | |

### `catalog_cross_matches`

| Column | Type | Notes |
|--------|------|-------|
| match_uuid | UUID, PK | |
| object_uuid | FK -> astronomical_objects | |
| catalog_name | str | "simbad", "ned", "sdss", "gaia" |
| catalog_source_id | str | Identifier within that catalog |
| angular_separation_arcseconds | float | |
| match_probability_score | float, nullable | |
| raw_catalog_response | JSONB | Full catalog response data |

Spatial indexes on `astronomical_objects` deferred until Phase 4 when objects exist.

## FastAPI Health Endpoint

```
GET /health -> 200 (all healthy) or 503 (any service down)
{
  "status": "healthy",
  "services": {
    "postgresql": {"status": "connected", "version": "17.x"},
    "redis": {"status": "connected"},
    "minio": {"status": "connected", "buckets": ["fits-raw", "tiles"]},
    "neo4j": {"status": "connected", "version": "5.x"}
  }
}
```

## Test Upload Endpoint

```
POST /test/upload -> 200
  Accepts a file, uploads to MinIO fits-raw bucket,
  creates observations record in PostgreSQL,
  returns observation_uuid and MinIO object key.
```

Temporary endpoint for validating success criterion #4. Will be removed or moved behind admin flag in later phases.

## Configuration (pydantic-settings)

Environment variables with `.env` file support:

- `DATABASE_URL` -- Postgres connection string
- `REDIS_URL` -- Redis connection string
- `S3_ENDPOINT_URL` -- MinIO/S3 endpoint (default: http://localhost:9000)
- `S3_ACCESS_KEY`, `S3_SECRET_KEY` -- MinIO/S3 credentials
- `S3_BUCKET_FITS_RAW`, `S3_BUCKET_TILES` -- Bucket names
- `NEO4J_URI` -- Neo4j Bolt URI
- `NEO4J_USER`, `NEO4J_PASSWORD` -- Neo4j credentials

## Celery No-Op Task

Single test task in `pipeline/tasks/test_noop.py` that accepts an observation_uuid, does no processing, and returns a completion result. Proves the full Celery chain: enqueue via Redis, execute on worker, report result back.

## Next.js Scaffold

Bare `create-next-app` with App Router, TypeScript, Tailwind CSS. Single placeholder page. No API integration until Phase 3.

## Testing Strategy

| Test | Validates | Requires |
|------|-----------|----------|
| test_health.py | Success criterion #3: all services connected | Docker Compose running |
| test_celery.py | Success criterion #2: Celery task chain works | Docker Compose + Celery worker running |
| test_minio.py | Success criterion #4: upload + metadata record | Docker Compose + FastAPI running |

Tests use pytest with httpx.AsyncClient for FastAPI endpoints.

---
*Design approved: 2026-02-21*
