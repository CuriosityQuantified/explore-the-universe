"""Integration tests for the ingest pipeline.

Tests the POST /api/ingest and GET /api/ingest/{uuid}/status endpoints,
plus a full end-to-end pipeline integration test that verifies a real
JWST observation flows through download -> validate_wcs -> generate_tiles.

Prerequisites for all tests:
- Docker Compose services running (PostgreSQL, Redis, MinIO)
- FastAPI server running: uvicorn api.main:app --host 0.0.0.0 --port 8000

Additional prerequisites for test_full_pipeline_integration:
- Celery worker running: celery -A pipeline.celery_app worker --loglevel=info
- Internet access (downloads from MAST / STScI servers)
- libvips installed (brew install vips on macOS)
- DYLD_LIBRARY_PATH=/opt/homebrew/lib set for the Celery worker (macOS)

Run quick tests only:
    pytest tests/test_ingest_pipeline.py -v -m "not slow"

Run full pipeline test:
    pytest tests/test_ingest_pipeline.py::test_full_pipeline_integration -v -s
"""

import time
import uuid

import boto3
import pytest
from httpx import Client, ConnectError

from shared.config import settings

BASE_URL = "http://localhost:8000"

# Known public JWST NIRCam observation from program 2731 (JADES)
# This is a single detector file, relatively small for integration testing.
TEST_ARCHIVE_OBSERVATION_ID = "jw02731001001_04101_00001_nrca1"


def _server_is_running() -> bool:
    """Check if the FastAPI server is reachable."""
    try:
        with Client(base_url=BASE_URL, timeout=5.0) as client:
            response = client.get("/health")
            return response.status_code in (200, 503)
    except (ConnectError, Exception):
        return False


server_running = pytest.mark.skipif(
    not _server_is_running(),
    reason="FastAPI server not running at localhost:8000",
)


@server_running
def test_trigger_ingest_returns_202():
    """POST /api/ingest should return 202 with observation_uuid and status."""
    with Client(base_url=BASE_URL, timeout=30.0) as client:
        response = client.post(
            "/api/ingest",
            json={
                "archive_observation_id": TEST_ARCHIVE_OBSERVATION_ID,
            },
        )

    assert response.status_code == 202, (
        f"Expected 202, got {response.status_code}: {response.text}"
    )

    data = response.json()
    assert "observation_uuid" in data
    assert data["status"] == "pipeline_started"

    # Verify observation_uuid is a valid UUID string
    try:
        uuid.UUID(data["observation_uuid"])
    except ValueError:
        pytest.fail(
            f"observation_uuid is not a valid UUID: {data['observation_uuid']}"
        )


@server_running
def test_trigger_ingest_missing_obs_id_returns_422():
    """POST /api/ingest with empty body should return 422 validation error."""
    with Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post("/api/ingest", json={})

    assert response.status_code == 422, (
        f"Expected 422, got {response.status_code}: {response.text}"
    )


@server_running
def test_ingest_status_returns_observation():
    """GET /api/ingest/{uuid}/status should return observation details."""
    with Client(base_url=BASE_URL, timeout=30.0) as client:
        # First trigger an ingest
        trigger_response = client.post(
            "/api/ingest",
            json={
                "archive_observation_id": (
                    f"test_status_{uuid.uuid4().hex[:8]}"
                ),
            },
        )
        assert trigger_response.status_code == 202
        observation_uuid = trigger_response.json()["observation_uuid"]

        # Check status
        status_response = client.get(
            f"/api/ingest/{observation_uuid}/status"
        )

    assert status_response.status_code == 200, (
        f"Expected 200, got {status_response.status_code}: "
        f"{status_response.text}"
    )

    data = status_response.json()
    assert data["observation_uuid"] == observation_uuid
    assert "archive_observation_id" in data
    assert "pipeline_status" in data

    valid_statuses = [
        "pending",
        "downloading",
        "processing",
        "completed",
        "failed",
    ]
    assert data["pipeline_status"] in valid_statuses, (
        f"Unexpected pipeline_status: {data['pipeline_status']}"
    )


@server_running
def test_ingest_status_unknown_uuid_returns_404():
    """GET /api/ingest/{uuid}/status with unknown UUID should return 404."""
    unknown_uuid = "00000000-0000-0000-0000-000000000000"

    with Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.get(f"/api/ingest/{unknown_uuid}/status")

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.text}"
    )


@server_running
@pytest.mark.slow
def test_full_pipeline_integration():
    """End-to-end test: ingest a real JWST observation through the full pipeline.

    This test triggers the full pipeline for a known JWST NIRCam observation,
    polls for completion, then verifies:
    1. Pipeline reaches 'completed' status
    2. All 3 processing steps (download, validate_wcs, generate_tiles) completed
    3. DZI tiles exist in MinIO tiles bucket
    4. Observation has pointing RA/Dec coordinates

    Prerequisites:
    - Docker Compose services (PostgreSQL, Redis, MinIO)
    - FastAPI server (uvicorn api.main:app)
    - Celery worker (celery -A pipeline.celery_app worker)
    - Internet access (MAST downloads)
    - libvips installed (brew install vips)
    - DYLD_LIBRARY_PATH=/opt/homebrew/lib for Celery worker on macOS

    This test may take several minutes due to MAST download time.
    """
    poll_interval_seconds = 10
    max_wait_seconds = 600  # 10 minutes

    with Client(base_url=BASE_URL, timeout=30.0) as client:
        # --- Step 1: Trigger ingest ---
        trigger_response = client.post(
            "/api/ingest",
            json={
                "archive_observation_id": TEST_ARCHIVE_OBSERVATION_ID,
            },
        )
        assert trigger_response.status_code == 202
        observation_uuid = trigger_response.json()["observation_uuid"]

        print(f"\nTriggered ingest for observation {observation_uuid}")
        print(
            f"Archive observation ID: {TEST_ARCHIVE_OBSERVATION_ID}"
        )

        # --- Step 2: Poll for completion ---
        elapsed_seconds = 0
        final_status = None
        final_data = None

        while elapsed_seconds < max_wait_seconds:
            status_response = client.get(
                f"/api/ingest/{observation_uuid}/status"
            )
            assert status_response.status_code == 200

            final_data = status_response.json()
            final_status = final_data["pipeline_status"]

            print(
                f"  [{elapsed_seconds:>3d}s] pipeline_status: {final_status}, "
                f"steps: {len(final_data.get('steps', []))}"
            )

            if final_status in ("completed", "failed"):
                break

            time.sleep(poll_interval_seconds)
            elapsed_seconds += poll_interval_seconds

        # --- Step 3: Assert pipeline completed ---
        assert final_status == "completed", (
            f"Pipeline did not complete within {max_wait_seconds}s. "
            f"Final status: {final_status}. "
            f"Steps: {final_data.get('steps', [])}"
        )

        # --- Step 4: Verify all 3 processing steps completed ---
        steps = final_data["steps"]
        step_names = [step["step_name"] for step in steps]

        assert "download" in step_names, (
            f"Missing 'download' step. Found: {step_names}"
        )
        assert "validate_wcs" in step_names, (
            f"Missing 'validate_wcs' step. Found: {step_names}"
        )
        assert "generate_tiles" in step_names, (
            f"Missing 'generate_tiles' step. Found: {step_names}"
        )

        for step in steps:
            assert step["step_status"] == "completed", (
                f"Step '{step['step_name']}' has status "
                f"'{step['step_status']}', expected 'completed'. "
                f"Error: {step.get('error_message_text')}"
            )

        # --- Step 5: Verify tiles exist in MinIO ---
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

        tile_objects = s3_client.list_objects_v2(
            Bucket=settings.s3_bucket_tiles,
            Prefix=f"{observation_uuid}/",
        )

        assert "Contents" in tile_objects, (
            f"No tile objects found in MinIO for observation {observation_uuid}"
        )

        tile_keys = [obj["Key"] for obj in tile_objects["Contents"]]
        dzi_files = [k for k in tile_keys if k.endswith(".dzi")]
        jpg_files = [k for k in tile_keys if k.endswith(".jpg")]

        assert len(dzi_files) >= 1, (
            f"Expected at least 1 .dzi file, found {len(dzi_files)}"
        )
        assert len(jpg_files) >= 1, (
            f"Expected at least 1 .jpg tile file, found {len(jpg_files)}"
        )

        print(
            f"\n  Tiles verified: {len(dzi_files)} DZI files, "
            f"{len(jpg_files)} JPEG tiles"
        )

        # --- Step 6: Verify Observation has pointing coordinates ---
        provenance = final_data.get("provenance", {})
        assert provenance is not None, "Provenance data is missing"
        assert provenance.get("pointing_ra_degrees") is not None, (
            "pointing_ra_degrees is None -- WCS extraction may have failed"
        )
        assert provenance.get("pointing_dec_degrees") is not None, (
            "pointing_dec_degrees is None -- WCS extraction may have failed"
        )

        print(
            f"  Pointing: RA={provenance['pointing_ra_degrees']:.6f}, "
            f"Dec={provenance['pointing_dec_degrees']:.6f}"
        )
        print(f"\n  Full pipeline integration test PASSED")
