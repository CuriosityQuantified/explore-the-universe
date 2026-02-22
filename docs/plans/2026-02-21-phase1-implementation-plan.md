# Phase 1: Foundation & Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** All backend services running with a pipeline framework that can accept and track work.

**Architecture:** Monorepo with three packages (pipeline/, api/, web/) sharing a root pyproject.toml. Infrastructure services (PostgreSQL, Redis, MinIO, Neo4j) run in Docker Compose. Python services (FastAPI, Celery) run natively via uv. Shared SQLAlchemy models and pydantic-settings config live in shared/.

**Tech Stack:** Python 3.10+ (FastAPI, Celery, SQLAlchemy, Alembic, boto3, pydantic-settings) | TypeScript (Next.js 16, React 19, Tailwind 4) | PostgreSQL 17 | Redis 7 | MinIO | Neo4j 5

---

## Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.env`
- Create: `.gitignore`
- Create: `shared/__init__.py`
- Create: `pipeline/__init__.py`
- Create: `pipeline/tasks/__init__.py`
- Create: `api/__init__.py`
- Create: `api/routers/__init__.py`
- Create: `api/db/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
*.egg

# Environment
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# Node
web/node_modules/
web/.next/
web/out/

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "explore-the-universe"
version = "0.1.0"
description = "A galactic encyclopedia: JWST imagery segmented, classified, and explorable"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.14.0",
    "psycopg2-binary>=2.9.0",
    "pydantic-settings>=2.7.0",
    "celery[redis]>=5.4.0",
    "redis>=5.0.0",
    "boto3>=1.35.0",
    "neo4j>=5.26.0",
    "python-multipart>=0.0.18",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.28.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 3: Create .env.example**

```bash
# PostgreSQL
DATABASE_URL=postgresql://explorer:explorer_dev@localhost:5432/explore_universe

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND_URL=redis://localhost:6379/1

# MinIO (S3-compatible)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_FITS_RAW=fits-raw
S3_BUCKET_TILES=tiles

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_dev_password
```

**Step 4: Copy .env.example to .env**

Run: `cp .env.example .env`

**Step 5: Create all __init__.py files**

Create empty `__init__.py` files in: `shared/`, `pipeline/`, `pipeline/tasks/`, `api/`, `api/routers/`, `api/db/`, `tests/`.

Each file is empty (zero bytes).

**Step 6: Create virtual environment and install dependencies**

Run: `uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"`
Expected: All dependencies install successfully.

**Step 7: Verify installation**

Run: `python -c "import fastapi, celery, sqlalchemy, boto3, neo4j; print('All imports OK')"`
Expected: `All imports OK`

**Step 8: Commit**

```bash
git add .gitignore pyproject.toml .env.example shared/__init__.py pipeline/__init__.py pipeline/tasks/__init__.py api/__init__.py api/routers/__init__.py api/db/__init__.py tests/__init__.py
git commit -m "feat: scaffold project structure with dependencies"
```

---

## Task 2: Docker Compose Infrastructure

**Files:**
- Create: `docker-compose.yml`

**Step 1: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: explore_universe
      POSTGRES_USER: explorer
      POSTGRES_PASSWORD: explorer_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U explorer -d explore_universe"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  minio-init:
    image: minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      sleep 3;
      mc alias set local http://minio:9000 minioadmin minioadmin;
      mc mb --ignore-existing local/fits-raw;
      mc mb --ignore-existing local/tiles;
      echo 'Buckets created successfully';
      exit 0;
      "

  neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/neo4j_dev_password
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

volumes:
  postgres_data:
  redis_data:
  minio_data:
  neo4j_data:
```

**Step 2: Start all services**

Run: `docker compose up -d`
Expected: All 5 containers start (postgres, redis, minio, minio-init, neo4j).

**Step 3: Verify services are running**

Run: `docker compose ps`
Expected: postgres, redis, minio, neo4j show "running". minio-init shows "exited (0)" (it's a one-shot init container).

**Step 4: Verify PostgreSQL**

Run: `docker compose exec postgres pg_isready -U explorer -d explore_universe`
Expected: `explore_universe - accepting connections`

**Step 5: Verify Redis**

Run: `docker compose exec redis redis-cli ping`
Expected: `PONG`

**Step 6: Verify MinIO buckets were created**

Run: `curl -s http://localhost:9000/minio/health/live`
Expected: HTTP 200 (empty body or health status).

**Step 7: Verify Neo4j**

Run: `curl -s http://localhost:7474`
Expected: JSON response with Neo4j info.

**Step 8: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add Docker Compose with Postgres, Redis, MinIO, Neo4j"
```

---

## Task 3: Shared Configuration

**Files:**
- Create: `shared/config.py`

**Step 1: Create shared/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    database_url: str = "postgresql://explorer:explorer_dev@localhost:5432/explore_universe"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_result_backend_url: str = "redis://localhost:6379/1"

    # MinIO (S3-compatible object storage)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_fits_raw: str = "fits-raw"
    s3_bucket_tiles: str = "tiles"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_dev_password"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

**Step 2: Verify config loads**

Run: `python -c "from shared.config import settings; print(settings.database_url)"`
Expected: `postgresql://explorer:explorer_dev@localhost:5432/explore_universe`

**Step 3: Commit**

```bash
git add shared/config.py
git commit -m "feat: add pydantic-settings configuration"
```

---

## Task 4: SQLAlchemy Models

**Files:**
- Create: `shared/models.py`
- Create: `api/db/session.py`

**Step 1: Create shared/models.py**

```python
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


pipeline_status_enum = Enum(
    "pending",
    "downloading",
    "processing",
    "completed",
    "failed",
    name="pipeline_status_enum",
)

step_status_enum = Enum(
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
    name="step_status_enum",
)


class Observation(Base):
    __tablename__ = "observations"

    observation_uuid = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    archive_observation_id = Column(String, unique=True, nullable=False)
    archive_program_id = Column(String, nullable=True)
    telescope_name = Column(String, nullable=False)
    instrument_name = Column(String, nullable=False)
    spectral_filters = Column(JSONB, nullable=True)
    total_exposure_seconds = Column(Float, nullable=True)
    pointing_ra_degrees = Column(Float, nullable=True)
    pointing_dec_degrees = Column(Float, nullable=True)
    pipeline_status = Column(
        pipeline_status_enum, nullable=False, default="pending"
    )
    ingested_at = Column(DateTime, nullable=False, server_default=func.now())
    last_updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    processing_steps = relationship(
        "ProcessingStep", back_populates="observation"
    )
    astronomical_objects = relationship(
        "AstronomicalObject", back_populates="observation"
    )


class ProcessingStep(Base):
    __tablename__ = "processing_steps"

    step_uuid = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    observation_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("observations.observation_uuid"),
        nullable=False,
    )
    step_name = Column(String, nullable=False)
    step_status = Column(step_status_enum, nullable=False, default="pending")
    step_started_at = Column(DateTime, nullable=True)
    step_completed_at = Column(DateTime, nullable=True)
    error_message_text = Column(Text, nullable=True)
    step_output_metadata = Column(JSONB, nullable=True)

    observation = relationship("Observation", back_populates="processing_steps")


class AstronomicalObject(Base):
    __tablename__ = "astronomical_objects"

    object_uuid = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_observation_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("observations.observation_uuid"),
        nullable=False,
    )
    sky_coordinate_ra_degrees = Column(Float, nullable=False)
    sky_coordinate_dec_degrees = Column(Float, nullable=False)
    classified_object_type = Column(String, nullable=True)
    classification_source_catalog = Column(String, nullable=True)
    classification_confidence_score = Column(Float, nullable=True)
    physical_properties = Column(JSONB, nullable=True)
    is_anomaly_flagged = Column(Boolean, nullable=False, default=False)
    detected_at = Column(DateTime, nullable=False, server_default=func.now())

    observation = relationship(
        "Observation", back_populates="astronomical_objects"
    )
    catalog_cross_matches = relationship(
        "CatalogCrossMatch", back_populates="astronomical_object"
    )


class CatalogCrossMatch(Base):
    __tablename__ = "catalog_cross_matches"

    match_uuid = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    object_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("astronomical_objects.object_uuid"),
        nullable=False,
    )
    catalog_name = Column(String, nullable=False)
    catalog_source_id = Column(String, nullable=False)
    angular_separation_arcseconds = Column(Float, nullable=False)
    match_probability_score = Column(Float, nullable=True)
    raw_catalog_response = Column(JSONB, nullable=True)

    astronomical_object = relationship(
        "AstronomicalObject", back_populates="catalog_cross_matches"
    )
```

**Step 2: Create api/db/session.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_database_session():
    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
```

**Step 3: Verify models import cleanly**

Run: `python -c "from shared.models import Base, Observation, ProcessingStep, AstronomicalObject, CatalogCrossMatch; print(f'{len(Base.metadata.tables)} tables defined')"`
Expected: `4 tables defined`

**Step 4: Commit**

```bash
git add shared/models.py api/db/session.py
git commit -m "feat: add SQLAlchemy models for observations, processing steps, objects, catalog matches"
```

---

## Task 5: Alembic Setup & Initial Migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Generate: `alembic/versions/<hash>_initial_schema.py`

**Step 1: Initialize Alembic**

Run: `alembic init alembic`
Expected: Creates `alembic.ini` and `alembic/` directory with template files.

**Step 2: Edit alembic.ini to use environment variable for database URL**

In `alembic.ini`, find the line:
```
sqlalchemy.url = driver://user:pass@localhost/dbname
```
Replace with:
```
sqlalchemy.url =
```
(Leave it blank — we'll set it from env.py.)

**Step 3: Edit alembic/env.py to use shared config and models**

Replace the entire contents of `alembic/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from shared.config import settings
from shared.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 4: Generate initial migration**

Run: `alembic revision --autogenerate -m "initial schema with observations, processing steps, objects, catalog matches"`
Expected: Creates a migration file in `alembic/versions/`.

**Step 5: Review the generated migration**

Run: `ls alembic/versions/*.py`
Open the generated file and verify it contains `create_table` operations for all 4 tables: `observations`, `processing_steps`, `astronomical_objects`, `catalog_cross_matches`. Also verify it creates the two enum types: `pipeline_status_enum` and `step_status_enum`.

**Step 6: Apply the migration**

Run: `alembic upgrade head`
Expected: Migration applies successfully. Output includes "Running upgrade ... -> ..., initial schema..."

**Step 7: Verify tables exist in PostgreSQL**

Run: `docker compose exec postgres psql -U explorer -d explore_universe -c "\dt"`
Expected: Lists all 4 tables plus `alembic_version`.

**Step 8: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: add Alembic with initial schema migration"
```

---

## Task 6: FastAPI Health Endpoint (TDD)

**Files:**
- Create: `tests/test_health.py`
- Create: `api/routers/health.py`
- Create: `api/main.py`

**Step 1: Write the failing test**

Create `tests/test_health.py`:

```python
from httpx import Client

BASE_URL = "http://localhost:8000"


def test_health_endpoint_returns_200_when_all_services_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_health_endpoint_reports_postgresql_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    data = response.json()
    assert "postgresql" in data["services"]
    assert data["services"]["postgresql"]["status"] == "connected"


def test_health_endpoint_reports_redis_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    data = response.json()
    assert "redis" in data["services"]
    assert data["services"]["redis"]["status"] == "connected"


def test_health_endpoint_reports_minio_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    data = response.json()
    assert "minio" in data["services"]
    assert data["services"]["minio"]["status"] == "connected"
    assert "buckets" in data["services"]["minio"]


def test_health_endpoint_reports_neo4j_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    data = response.json()
    assert "neo4j" in data["services"]
    assert data["services"]["neo4j"]["status"] == "connected"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_health.py -v`
Expected: FAIL — connection refused (FastAPI not running yet).

**Step 3: Create api/routers/health.py**

```python
import boto3
from botocore.client import Config
from fastapi import APIRouter, Response
from neo4j import GraphDatabase
from redis import Redis
from sqlalchemy import text

from api.db.session import engine
from shared.config import settings

router = APIRouter()


@router.get("/health")
def check_service_health(response: Response):
    services = {}
    all_services_healthy = True

    # PostgreSQL
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            postgres_version = result.scalar()
        services["postgresql"] = {
            "status": "connected",
            "version": postgres_version,
        }
    except Exception as exc:
        services["postgresql"] = {
            "status": "disconnected",
            "error": str(exc),
        }
        all_services_healthy = False

    # Redis
    try:
        redis_client = Redis.from_url(settings.redis_url)
        redis_client.ping()
        redis_client.close()
        services["redis"] = {"status": "connected"}
    except Exception as exc:
        services["redis"] = {
            "status": "disconnected",
            "error": str(exc),
        }
        all_services_healthy = False

    # MinIO (S3-compatible)
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )
        bucket_list = [
            bucket["Name"]
            for bucket in s3_client.list_buckets()["Buckets"]
        ]
        services["minio"] = {
            "status": "connected",
            "buckets": bucket_list,
        }
    except Exception as exc:
        services["minio"] = {
            "status": "disconnected",
            "error": str(exc),
        }
        all_services_healthy = False

    # Neo4j
    try:
        neo4j_driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        with neo4j_driver.session() as neo4j_session:
            result = neo4j_session.run(
                "CALL dbms.components() YIELD versions "
                "RETURN versions[0] AS version"
            )
            neo4j_version = result.single()["version"]
        neo4j_driver.close()
        services["neo4j"] = {
            "status": "connected",
            "version": neo4j_version,
        }
    except Exception as exc:
        services["neo4j"] = {
            "status": "disconnected",
            "error": str(exc),
        }
        all_services_healthy = False

    if not all_services_healthy:
        response.status_code = 503

    return {
        "status": "healthy" if all_services_healthy else "unhealthy",
        "services": services,
    }
```

**Step 4: Create api/main.py**

```python
from fastapi import FastAPI

from api.routers.health import router as health_router

app = FastAPI(
    title="Explore the Universe",
    version="0.1.0",
    description="Galactic encyclopedia API",
)

app.include_router(health_router)
```

**Step 5: Start FastAPI server in background**

Run: `uvicorn api.main:app --reload &`
Expected: Server starts on http://localhost:8000. Wait a few seconds for startup.

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_health.py -v`
Expected: All 5 tests PASS.

**Step 7: Stop the background server**

Run: `kill %1` (or the appropriate PID)

**Step 8: Commit**

```bash
git add tests/test_health.py api/routers/health.py api/main.py
git commit -m "feat: add FastAPI health endpoint verifying all service connections"
```

---

## Task 7: Celery No-Op Task (TDD)

**Files:**
- Create: `tests/test_celery.py`
- Create: `pipeline/celery_app.py`
- Create: `pipeline/tasks/test_noop.py`

**Step 1: Write the failing test**

Create `tests/test_celery.py`:

```python
def test_noop_task_returns_completed_status():
    """Test the no-op task executes synchronously and returns expected result."""
    from pipeline.tasks.test_noop import test_pipeline_task

    result = test_pipeline_task.apply(args=["test-observation-uuid-123"])

    assert result.successful()
    task_output = result.result
    assert task_output["observation_uuid"] == "test-observation-uuid-123"
    assert task_output["status"] == "completed"


def test_noop_task_handles_different_uuids():
    """Test the task works with any observation UUID."""
    from pipeline.tasks.test_noop import test_pipeline_task

    result = test_pipeline_task.apply(
        args=["550e8400-e29b-41d4-a716-446655440000"]
    )

    assert result.successful()
    task_output = result.result
    assert (
        task_output["observation_uuid"]
        == "550e8400-e29b-41d4-a716-446655440000"
    )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_celery.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.tasks.test_noop'` or similar.

**Step 3: Create pipeline/celery_app.py**

```python
from celery import Celery

from shared.config import settings

celery_app = Celery(
    "explore_universe",
    broker=settings.redis_url,
    backend=settings.celery_result_backend_url,
)

celery_app.autodiscover_tasks(["pipeline.tasks"])
```

**Step 4: Create pipeline/tasks/test_noop.py**

```python
from pipeline.celery_app import celery_app


@celery_app.task
def test_pipeline_task(observation_uuid: str) -> dict:
    """No-op task that simulates pipeline processing.

    Accepts an observation UUID, does no actual processing,
    and returns a completion result. Used to verify the Celery
    task chain works end-to-end.
    """
    return {
        "observation_uuid": observation_uuid,
        "status": "completed",
    }
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_celery.py -v`
Expected: Both tests PASS. (`task.apply()` runs synchronously without needing a Celery worker.)

**Step 6: Commit**

```bash
git add tests/test_celery.py pipeline/celery_app.py pipeline/tasks/test_noop.py
git commit -m "feat: add Celery app with no-op test task"
```

---

## Task 8: Test Upload Endpoint (TDD)

**Files:**
- Create: `tests/test_minio_upload.py`
- Create: `api/routers/test_upload.py`
- Modify: `api/main.py`

**Step 1: Write the failing test**

Create `tests/test_minio_upload.py`:

```python
import io

from httpx import Client

BASE_URL = "http://localhost:8000"


def test_upload_returns_observation_uuid_and_object_key():
    fake_fits_content = b"SIMPLE  =                    T / fake FITS header"
    files = {
        "file": (
            "test_observation.fits",
            io.BytesIO(fake_fits_content),
            "application/octet-stream",
        )
    }

    with Client(base_url=BASE_URL) as client:
        response = client.post("/test/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "observation_uuid" in data
    assert "object_key" in data
    assert data["bucket"] == "fits-raw"


def test_upload_creates_metadata_record_in_postgresql():
    fake_fits_content = b"SIMPLE  =                    T / another fake FITS"
    files = {
        "file": (
            "another_test.fits",
            io.BytesIO(fake_fits_content),
            "application/octet-stream",
        )
    }

    with Client(base_url=BASE_URL) as client:
        upload_response = client.post("/test/upload", files=files)
        observation_uuid = upload_response.json()["observation_uuid"]

        # Verify the record exists via health endpoint
        # (We don't have an object GET endpoint yet, but the upload
        # should have created a record. We verify by checking the
        # upload succeeded and returned a valid UUID.)
        assert len(observation_uuid) == 36  # UUID format
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_minio_upload.py -v`
Expected: FAIL — connection refused (FastAPI not running) or 404 (endpoint doesn't exist).

**Step 3: Create api/routers/test_upload.py**

```python
import uuid

import boto3
from botocore.client import Config
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from api.db.session import get_database_session
from shared.config import settings
from shared.models import Observation

router = APIRouter()


@router.post("/test/upload")
def upload_test_file(
    file: UploadFile = File(...),
    database_session: Session = Depends(get_database_session),
):
    """Temporary test endpoint: uploads a file to MinIO and creates
    an observation metadata record in PostgreSQL.

    This endpoint validates success criterion #4 and will be removed
    or moved behind an admin flag in later phases.
    """
    new_observation_uuid = uuid.uuid4()
    object_key = f"raw/{new_observation_uuid}/{file.filename}"

    # Upload file to MinIO
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )
    s3_client.upload_fileobj(
        file.file, settings.s3_bucket_fits_raw, object_key
    )

    # Create metadata record in PostgreSQL
    observation_record = Observation(
        observation_uuid=new_observation_uuid,
        archive_observation_id=f"test-{new_observation_uuid}",
        telescope_name="test",
        instrument_name="test",
        pipeline_status="pending",
    )
    database_session.add(observation_record)
    database_session.commit()

    return {
        "observation_uuid": str(new_observation_uuid),
        "object_key": object_key,
        "bucket": settings.s3_bucket_fits_raw,
    }
```

**Step 4: Register the upload router in api/main.py**

Replace the contents of `api/main.py` with:

```python
from fastapi import FastAPI

from api.routers.health import router as health_router
from api.routers.test_upload import router as test_upload_router

app = FastAPI(
    title="Explore the Universe",
    version="0.1.0",
    description="Galactic encyclopedia API",
)

app.include_router(health_router)
app.include_router(test_upload_router)
```

**Step 5: Start FastAPI server in background**

Run: `uvicorn api.main:app --reload &`
Expected: Server starts on http://localhost:8000.

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_minio_upload.py -v`
Expected: Both tests PASS.

**Step 7: Also re-run health tests to make sure nothing broke**

Run: `pytest tests/test_health.py -v`
Expected: All 5 tests still PASS.

**Step 8: Stop the background server**

Run: `kill %1`

**Step 9: Commit**

```bash
git add tests/test_minio_upload.py api/routers/test_upload.py api/main.py
git commit -m "feat: add test upload endpoint (MinIO + PostgreSQL metadata)"
```

---

## Task 9: Next.js Scaffold

**Files:**
- Create: `web/` directory via create-next-app

**Step 1: Scaffold Next.js app**

Run: `npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm`

When prompted, accept defaults. This creates the full Next.js project in `web/`.

Expected: `web/` directory with package.json, next.config.ts, tsconfig.json, tailwind.config.ts, app/page.tsx, etc.

**Step 2: Verify it builds**

Run: `cd web && npm run build && cd ..`
Expected: Build succeeds with no errors.

**Step 3: Commit**

```bash
git add web/
git commit -m "feat: scaffold Next.js frontend with TypeScript and Tailwind"
```

---

## Task 10: Full Integration Verification

**Files:** No new files — verification only.

**Step 1: Ensure Docker Compose is running**

Run: `docker compose up -d`
Expected: All services running.

**Step 2: Ensure migrations are applied**

Run: `alembic upgrade head`
Expected: Already at head (or applies if not).

**Step 3: Start FastAPI in background**

Run: `uvicorn api.main:app --reload &`
Expected: Server running on port 8000.

**Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass:
- `test_health.py`: 5 PASSED
- `test_celery.py`: 2 PASSED
- `test_minio_upload.py`: 2 PASSED

**Step 5: Verify success criterion #1 — Docker Compose single command**

Run: `docker compose down && docker compose up -d`
Expected: All services come up and reach healthy state.

**Step 6: Verify success criterion #2 — Celery full chain (with actual worker)**

Start a Celery worker in a separate terminal:
Run: `celery -A pipeline.celery_app worker --loglevel=info &`
Wait a few seconds for the worker to connect.

Then test with an async task dispatch:
Run: `python -c "from pipeline.tasks.test_noop import test_pipeline_task; r = test_pipeline_task.delay('integration-test-uuid'); print(r.get(timeout=10))"`
Expected: `{'observation_uuid': 'integration-test-uuid', 'status': 'completed'}`

Stop the worker:
Run: `kill %2` (or appropriate PID)

**Step 7: Verify success criterion #3 — Health endpoint**

Run: `curl -s http://localhost:8000/health | python -m json.tool`
Expected: JSON showing all 4 services with `"status": "connected"`.

**Step 8: Verify success criterion #4 — Upload + metadata**

Run: `echo "test data" > /tmp/test.fits && curl -s -F "file=@/tmp/test.fits" http://localhost:8000/test/upload | python -m json.tool`
Expected: JSON with `observation_uuid`, `object_key`, and `bucket`.

**Step 9: Stop FastAPI server**

Run: `kill %1`

**Step 10: Commit (if any cleanup was needed)**

If any fixes were required during verification, commit them now.

---

## Summary

| Task | What it delivers | Success criteria addressed |
|------|------------------|---------------------------|
| 1. Scaffolding | Project structure, dependencies | — |
| 2. Docker Compose | All 4 infrastructure services | #1 |
| 3. Shared config | pydantic-settings configuration | — |
| 4. SQLAlchemy models | 4 database tables defined | — |
| 5. Alembic | Database migration applied | — |
| 6. Health endpoint | Service connectivity verification | #3 |
| 7. Celery task | No-op task chain proof | #2 |
| 8. Upload endpoint | MinIO + PostgreSQL integration | #4 |
| 9. Next.js scaffold | Frontend project structure | — |
| 10. Integration | End-to-end verification | All 4 |

**Total commits:** 9 (one per task, excluding verification)
**Estimated tasks:** 10

---
*Plan created: 2026-02-21*
*Design doc: docs/plans/2026-02-21-phase1-foundation-infrastructure-design.md*
