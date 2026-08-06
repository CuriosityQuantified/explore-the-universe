"""Regression suite: Phase 5 Plan 3 — anomaly API endpoints.

All tests are offline — no network, no live DB, no running services required.
Uses FastAPI TestClient with a mock database session dependency.
"""

import uuid
import unittest.mock as mock
from datetime import datetime

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_with_mock_session(mock_session):
    """Return a TestClient wired with a mock DB session override."""
    from api.main import app
    from api.db.session import get_database_session

    app.dependency_overrides[get_database_session] = lambda: mock_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_database_session, None)


# ---------------------------------------------------------------------------
# GET /api/objects/{uuid}/classifications
# ---------------------------------------------------------------------------


def test_classifications_returns_404_for_unknown_object():
    from api.main import app
    from api.db.session import get_database_session

    mock_session = mock.MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_database_session] = lambda: mock_session
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{uuid.uuid4()}/classifications")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_database_session, None)


def test_classifications_returns_history_newest_first():
    from api.main import app
    from api.db.session import get_database_session
    from shared.models import AstronomicalObject, ObjectClassification

    obj_uuid = uuid.uuid4()
    clf_uuid_1 = uuid.uuid4()
    clf_uuid_2 = uuid.uuid4()

    mock_obj = mock.MagicMock(spec=AstronomicalObject)
    mock_obj.object_uuid = obj_uuid

    clf_old = mock.MagicMock(spec=ObjectClassification)
    clf_old.classification_uuid = clf_uuid_1
    clf_old.predicted_object_type = "star"
    clf_old.classification_confidence_score = 0.8
    clf_old.ml_model_version = "rf_v1.0"
    clf_old.feature_extractor_version = "statmorph_0.7+sep"
    clf_old.feature_vector = {"concentration": 1.2}
    clf_old.is_anomaly_flagged = False
    clf_old.anomaly_score = None
    clf_old.anomaly_explanation = None
    clf_old.classified_at = datetime(2026, 1, 1)

    clf_new = mock.MagicMock(spec=ObjectClassification)
    clf_new.classification_uuid = clf_uuid_2
    clf_new.predicted_object_type = "white_dwarf"
    clf_new.classification_confidence_score = 0.9
    clf_new.ml_model_version = "rf_v1.1"
    clf_new.feature_extractor_version = "statmorph_0.7+sep"
    clf_new.feature_vector = {"concentration": 1.5}
    clf_new.is_anomaly_flagged = True
    clf_new.anomaly_score = -0.42
    clf_new.anomaly_explanation = "Feature vector outlier"
    clf_new.classified_at = datetime(2026, 2, 1)

    mock_session = mock.MagicMock()

    def query_side_effect(model_class):
        q = mock.MagicMock()
        if model_class is AstronomicalObject:
            q.filter.return_value.first.return_value = mock_obj
        else:
            q.filter.return_value.order_by.return_value.all.return_value = [
                clf_new, clf_old
            ]
        return q

    mock_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_database_session] = lambda: mock_session
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/classifications")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["predicted_object_type"] == "white_dwarf"
        assert data[0]["is_anomaly_flagged"] is True
        assert data[0]["anomaly_explanation"] == "Feature vector outlier"
        assert data[1]["predicted_object_type"] == "star"
    finally:
        app.dependency_overrides.pop(get_database_session, None)


# ---------------------------------------------------------------------------
# GET /api/objects/{uuid}/cross-matches
# ---------------------------------------------------------------------------


def test_cross_matches_returns_404_for_unknown_object():
    from api.main import app
    from api.db.session import get_database_session

    mock_session = mock.MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_database_session] = lambda: mock_session
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{uuid.uuid4()}/cross-matches")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_database_session, None)


def test_cross_matches_ordered_by_angular_separation():
    from api.main import app
    from api.db.session import get_database_session
    from shared.models import AstronomicalObject, CatalogCrossMatch

    obj_uuid = uuid.uuid4()
    mock_obj = mock.MagicMock(spec=AstronomicalObject)
    mock_obj.object_uuid = obj_uuid

    match_close = mock.MagicMock(spec=CatalogCrossMatch)
    match_close.match_uuid = uuid.uuid4()
    match_close.catalog_name = "SIMBAD"
    match_close.catalog_source_id = "SIMBAD_001"
    match_close.angular_separation_arcseconds = 0.5
    match_close.match_probability_score = 0.95
    match_close.raw_catalog_response = {"type": "Star"}

    match_far = mock.MagicMock(spec=CatalogCrossMatch)
    match_far.match_uuid = uuid.uuid4()
    match_far.catalog_name = "Gaia"
    match_far.catalog_source_id = "GAIA_001"
    match_far.angular_separation_arcseconds = 2.3
    match_far.match_probability_score = 0.7
    match_far.raw_catalog_response = None

    mock_session = mock.MagicMock()

    def query_side_effect(model_class):
        q = mock.MagicMock()
        if model_class is AstronomicalObject:
            q.filter.return_value.first.return_value = mock_obj
        else:
            q.filter.return_value.order_by.return_value.all.return_value = [
                match_close, match_far
            ]
        return q

    mock_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_database_session] = lambda: mock_session
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/cross-matches")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["angular_separation_arcseconds"] == pytest.approx(0.5)
        assert data[0]["catalog_name"] == "SIMBAD"
        assert data[1]["angular_separation_arcseconds"] == pytest.approx(2.3)
    finally:
        app.dependency_overrides.pop(get_database_session, None)


# ---------------------------------------------------------------------------
# GET /api/observations/{uuid}/anomalies
# ---------------------------------------------------------------------------


def test_anomalies_returns_empty_list_when_none_found():
    """Returns [] (not 404) when no anomaly-flagged objects exist."""
    from api.main import app
    from api.db.session import get_database_session

    mock_session = mock.MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = []

    app.dependency_overrides[get_database_session] = lambda: mock_session
    try:
        client = TestClient(app)
        resp = client.get(f"/api/observations/{uuid.uuid4()}/anomalies")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_database_session, None)


def test_anomalies_returns_flagged_objects_with_explanation():
    from api.main import app
    from api.db.session import get_database_session
    from shared.models import AstronomicalObject, ObjectClassification

    obs_uuid = uuid.uuid4()
    obj_uuid = uuid.uuid4()

    flagged_obj = mock.MagicMock(spec=AstronomicalObject)
    flagged_obj.object_uuid = obj_uuid
    flagged_obj.sky_coordinate_ra_degrees = 83.82
    flagged_obj.sky_coordinate_dec_degrees = -5.39
    flagged_obj.classified_object_type = "star"
    flagged_obj.catalog_object_name = "Betelgeuse"
    flagged_obj.cutout_s3_prefix = "seg/obs/obj/"

    latest_clf = mock.MagicMock(spec=ObjectClassification)
    latest_clf.predicted_object_type = "spiral_galaxy"
    latest_clf.anomaly_score = -0.61
    latest_clf.anomaly_explanation = "ML type 'spiral_galaxy' disagrees with catalog type 'star'"

    mock_session = mock.MagicMock()

    def query_side_effect(model_class):
        q = mock.MagicMock()
        if model_class is AstronomicalObject:
            q.filter.return_value.all.return_value = [flagged_obj]
        else:
            q.filter.return_value.order_by.return_value.first.return_value = latest_clf
        return q

    mock_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_database_session] = lambda: mock_session
    try:
        client = TestClient(app)
        resp = client.get(f"/api/observations/{obs_uuid}/anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        entry = data[0]
        assert entry["object_uuid"] == str(obj_uuid)
        assert entry["predicted_object_type"] == "spiral_galaxy"
        assert entry["anomaly_score"] == pytest.approx(-0.61)
        assert "disagrees" in entry["anomaly_explanation"]
        assert entry["catalog_object_name"] == "Betelgeuse"
    finally:
        app.dependency_overrides.pop(get_database_session, None)


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------


def test_objects_router_registered_in_app():
    from api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = list(resp.json().get("paths", {}).keys())
    assert any("classifications" in p for p in paths), (
        f"classifications endpoint not registered. Paths: {paths}"
    )
    assert any("cross-matches" in p for p in paths), (
        f"cross-matches endpoint not registered. Paths: {paths}"
    )
    assert any("anomalies" in p for p in paths), (
        f"anomalies endpoint not registered. Paths: {paths}"
    )
