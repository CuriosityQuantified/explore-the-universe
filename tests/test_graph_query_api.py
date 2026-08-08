"""Regression suite: Issue #12 — graph query and neighborhood API.

GET /api/graph/query                    — filter AstronomicalObject nodes by properties
GET /api/objects/{uuid}/graph-neighbors — 1-hop neighborhood for a UUID

All tests are offline — no network, no live Neo4j, no running services required.
Uses FastAPI TestClient with a mock neo4j session dependency.
"""

import unittest.mock as mock
import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_neo4j_session(data: list) -> mock.MagicMock:
    """Return a mock neo4j Session whose .run().data() returns *data*."""
    session = mock.MagicMock()
    result = mock.MagicMock()
    result.data.return_value = data
    session.run.return_value = result
    return session


class graph_client:
    """Context manager: installs a mock neo4j session and yields a TestClient."""

    def __init__(self, mock_session, raise_server_exceptions: bool = True):
        from api.main import app
        from api.db.neo4j import get_neo4j_session

        self._app = app
        self._key = get_neo4j_session
        self._app.dependency_overrides[self._key] = lambda: mock_session
        self._client = TestClient(self._app, raise_server_exceptions=raise_server_exceptions)

    def __enter__(self) -> TestClient:
        return self._client

    def __exit__(self, *_):
        self._app.dependency_overrides.pop(self._key, None)
        return False


# ---------------------------------------------------------------------------
# Tests: GET /api/graph/query
# ---------------------------------------------------------------------------


def test_graph_query_returns_matching_objects():
    rows = [
        {"uuid": str(uuid.uuid4()), "type": "spiral_galaxy", "magnitude": 15.2,
         "redshift": 0.03, "ra": 83.82, "dec": -5.39},
        {"uuid": str(uuid.uuid4()), "type": "spiral_galaxy", "magnitude": 17.8,
         "redshift": 0.05, "ra": 84.10, "dec": -5.12},
    ]
    with graph_client(_mock_neo4j_session(rows)) as client:
        resp = client.get("/api/graph/query?type=spiral_galaxy")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) == 2
        assert body["results"][0]["type"] == "spiral_galaxy"


def test_graph_query_all_filters_optional():
    with graph_client(_mock_neo4j_session([])) as client:
        resp = client.get("/api/graph/query")
        assert resp.status_code == 200
        body = resp.json()
        assert body["results"] == []


def test_graph_query_magnitude_max_filter():
    mock_session = _mock_neo4j_session([])
    with graph_client(mock_session) as client:
        resp = client.get("/api/graph/query?magnitude_max=18.0")
        assert resp.status_code == 200
        # Verify the Cypher was called with the correct parameters.
        call_kwargs = mock_session.run.call_args.kwargs
        assert call_kwargs["magnitude_max"] == 18.0
        assert call_kwargs["type"] is None


def test_graph_query_is_parameterized_not_interpolated():
    """The endpoint must call session.run() — not do string formatting."""
    mock_session = _mock_neo4j_session([])
    with graph_client(mock_session) as client:
        client.get("/api/graph/query?type=elliptical&magnitude_max=20")
        assert mock_session.run.called, "neo4j_session.run must be called"
        # The first positional arg should be the Cypher string, not contain
        # the user's literal input interpolated as a substring.
        cypher_arg = mock_session.run.call_args.args[0]
        assert "elliptical" not in cypher_arg, (
            "User input must not be interpolated into the Cypher string"
        )


def test_graph_query_pagination():
    mock_session = _mock_neo4j_session([])
    with graph_client(mock_session) as client:
        resp = client.get("/api/graph/query?limit=10&offset=5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 10
        assert body["offset"] == 5
        # Verify skip/limit are forwarded to Cypher.
        call_kwargs = mock_session.run.call_args.kwargs
        assert call_kwargs["skip"] == 5
        assert call_kwargs["limit"] == 10


def test_graph_query_is_anomaly_filter():
    mock_session = _mock_neo4j_session([])
    with graph_client(mock_session) as client:
        resp = client.get("/api/graph/query?is_anomaly=true")
        assert resp.status_code == 200
        call_kwargs = mock_session.run.call_args.kwargs
        assert call_kwargs["is_anomaly"] is True


# ---------------------------------------------------------------------------
# Tests: GET /api/objects/{uuid}/graph-neighbors
# ---------------------------------------------------------------------------

_OBJ_UUID = str(uuid.uuid4())


def test_graph_neighbors_returns_contains_children():
    child_uuid = str(uuid.uuid4())
    rows = [{
        "contains_children": [{"uuid": child_uuid, "type": "star", "cutout_s3_prefix": "cuts/a"}],
        "contained_by": [],
        "catalog_entries": [],
    }]
    with graph_client(_mock_neo4j_session(rows)) as client:
        with mock.patch("api.routers.graph.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = "https://minio/cuts/a/cutout_stretched.png"
            resp = client.get(f"/api/objects/{_OBJ_UUID}/graph-neighbors")
        assert resp.status_code == 200
        body = resp.json()
        assert body["in_graph"] is True
        assert len(body["contains_children"]) == 1
        assert body["contains_children"][0]["uuid"] == child_uuid
        assert body["contains_children"][0]["type"] == "star"
        assert body["contains_children"][0]["thumbnail_url"] == "https://minio/cuts/a/cutout_stretched.png"


def test_graph_neighbors_returns_contained_by():
    parent_uuid = str(uuid.uuid4())
    rows = [{
        "contains_children": [],
        "contained_by": [{"uuid": parent_uuid, "type": "galaxy_cluster", "cutout_s3_prefix": None}],
        "catalog_entries": [],
    }]
    with graph_client(_mock_neo4j_session(rows)) as client:
        resp = client.get(f"/api/objects/{_OBJ_UUID}/graph-neighbors")
        assert resp.status_code == 200
        body = resp.json()
        assert body["in_graph"] is True
        assert len(body["contained_by"]) == 1
        assert body["contained_by"][0]["uuid"] == parent_uuid
        # No cutout_s3_prefix → thumbnail_url must be null
        assert body["contained_by"][0]["thumbnail_url"] is None


def test_graph_neighbors_returns_catalog_entries():
    rows = [{
        "contains_children": [],
        "contained_by": [],
        "catalog_entries": [
            {"catalog": "SIMBAD", "source_id": "NGC 1300"},
            {"catalog": "NED", "source_id": "NGC1300"},
        ],
    }]
    with graph_client(_mock_neo4j_session(rows)) as client:
        resp = client.get(f"/api/objects/{_OBJ_UUID}/graph-neighbors")
        assert resp.status_code == 200
        body = resp.json()
        assert body["in_graph"] is True
        assert len(body["catalog_entries"]) == 2
        catalogs = {e["catalog"] for e in body["catalog_entries"]}
        assert "SIMBAD" in catalogs
        assert "NED" in catalogs


def test_graph_neighbors_not_in_graph():
    """Empty Cypher result → in_graph: false."""
    with graph_client(_mock_neo4j_session([])) as client:
        resp = client.get(f"/api/objects/{_OBJ_UUID}/graph-neighbors")
        assert resp.status_code == 200
        body = resp.json()
        assert body["in_graph"] is False


def test_graph_neighbors_filters_null_entries():
    """OPTIONAL MATCH produces {uuid: null, ...} rows — these should be dropped."""
    rows = [{
        "contains_children": [
            {"uuid": None, "type": None, "cutout_s3_prefix": None},
            {"uuid": str(uuid.uuid4()), "type": "nebula", "cutout_s3_prefix": None},
        ],
        "contained_by": [{"uuid": None, "type": None, "cutout_s3_prefix": None}],
        "catalog_entries": [{"catalog": None, "source_id": None}],
    }]
    with graph_client(_mock_neo4j_session(rows)) as client:
        resp = client.get(f"/api/objects/{_OBJ_UUID}/graph-neighbors")
        assert resp.status_code == 200
        body = resp.json()
        assert body["in_graph"] is True
        assert len(body["contains_children"]) == 1
        assert body["contains_children"][0]["type"] == "nebula"
        assert len(body["contained_by"]) == 0
        assert len(body["catalog_entries"]) == 0


# ---------------------------------------------------------------------------
# Tests: error handling (503 on Neo4j failure)
# ---------------------------------------------------------------------------


def test_graph_query_returns_503_on_neo4j_error():
    """Neo4j driver exception must surface as 503, not a raw 500."""
    mock_session = mock.MagicMock()
    mock_session.run.side_effect = RuntimeError("connection refused")
    with graph_client(mock_session, raise_server_exceptions=False) as client:
        resp = client.get("/api/graph/query?type=spiral_galaxy")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Graph database unavailable"


def test_graph_neighbors_returns_503_on_neo4j_error():
    """Neo4j driver exception in neighbors endpoint must surface as 503."""
    mock_session = mock.MagicMock()
    mock_session.run.side_effect = RuntimeError("connection refused")
    with graph_client(mock_session, raise_server_exceptions=False) as client:
        resp = client.get(f"/api/objects/{_OBJ_UUID}/graph-neighbors")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Graph database unavailable"


# ---------------------------------------------------------------------------
# Tests: OpenAPI registration
# ---------------------------------------------------------------------------


def test_graph_endpoints_registered_in_openapi():
    with graph_client(_mock_neo4j_session([])) as client:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/graph/query" in paths, "/api/graph/query must appear in OpenAPI schema"
        assert "/api/objects/{uuid}/graph-neighbors" in paths, (
            "/api/objects/{uuid}/graph-neighbors must appear in OpenAPI schema"
        )
