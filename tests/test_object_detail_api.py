"""Regression suite: Phase 6 — object detail API endpoint.

GET /api/objects/{uuid}  — full object record, cross-matches, latest classification.

All tests are offline — no network, no live DB, no running services required.
Uses FastAPI TestClient with a mock database session dependency and a mock
S3 client (for presigned cutout URLs).
"""

import uuid
import unittest.mock as mock
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from shared.models import AstronomicalObject, CatalogCrossMatch, ObjectClassification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(mock_session):
    from api.main import app
    from api.db.session import get_database_session

    app.dependency_overrides[get_database_session] = lambda: mock_session
    return app


def _teardown(app):
    from api.db.session import get_database_session

    app.dependency_overrides.pop(get_database_session, None)


def _make_obj(
    obj_uuid=None,
    obs_uuid=None,
    ra=83.82,
    dec=-5.39,
    obj_type="spiral_galaxy",
    name="NGC 1977",
    magnitude=8.4,
    redshift=0.002,
    anomaly=False,
    cutout_prefix=None,
    physical_properties=None,
    mask_rle=None,
    bounding_box=None,
):
    obj = mock.MagicMock(spec=AstronomicalObject)
    obj.object_uuid = obj_uuid or uuid.uuid4()
    obj.source_observation_uuid = obs_uuid or uuid.uuid4()
    obj.sky_coordinate_ra_degrees = ra
    obj.sky_coordinate_dec_degrees = dec
    obj.classified_object_type = obj_type
    obj.catalog_object_name = name
    obj.catalog_magnitude = magnitude
    obj.catalog_redshift = redshift
    obj.is_anomaly_flagged = anomaly
    obj.cutout_s3_prefix = cutout_prefix
    obj.physical_properties = physical_properties
    obj.segmentation_mask_rle = mask_rle
    obj.bounding_box_pixels = bounding_box
    return obj


def _make_match(
    catalog="SIMBAD",
    source_id="SIMBAD_001",
    separation=0.5,
    probability=0.95,
):
    m = mock.MagicMock(spec=CatalogCrossMatch)
    m.match_uuid = uuid.uuid4()
    m.catalog_name = catalog
    m.catalog_source_id = source_id
    m.angular_separation_arcseconds = separation
    m.match_probability_score = probability
    m.raw_catalog_response = None
    return m


def _make_clf(
    clf_uuid=None,
    predicted_type="spiral_galaxy",
    confidence=0.93,
    model_version="rf_v1.1",
    anomaly_flagged=False,
    anomaly_score=None,
    anomaly_explanation=None,
    classified_at=None,
):
    clf = mock.MagicMock(spec=ObjectClassification)
    clf.classification_uuid = clf_uuid or uuid.uuid4()
    clf.predicted_object_type = predicted_type
    clf.classification_confidence_score = confidence
    clf.ml_model_version = model_version
    clf.feature_extractor_version = "statmorph_0.7+sep"
    clf.is_anomaly_flagged = anomaly_flagged
    clf.anomaly_score = anomaly_score
    clf.anomaly_explanation = anomaly_explanation
    clf.classified_at = classified_at or datetime(2026, 8, 1)
    return clf


def _session_for(obj, matches, latest_clf):
    """Return a mock session that dispatches correctly for the detail endpoint."""
    mock_session = mock.MagicMock()

    def query_side_effect(model_class):
        q = mock.MagicMock()
        if model_class is AstronomicalObject:
            q.filter.return_value.first.return_value = obj
        elif model_class is CatalogCrossMatch:
            q.filter.return_value.order_by.return_value.all.return_value = matches
        else:  # ObjectClassification
            q.filter.return_value.order_by.return_value.first.return_value = latest_clf
        return q

    mock_session.query.side_effect = query_side_effect
    return mock_session


# ---------------------------------------------------------------------------
# 404 for unknown UUID
# ---------------------------------------------------------------------------


def test_object_detail_404_for_unknown_uuid():
    mock_session = mock.MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    app = _make_app(mock_session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{uuid.uuid4()}")
        assert resp.status_code == 404
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Full record shape
# ---------------------------------------------------------------------------


def test_object_detail_returns_full_record():
    obj_uuid = uuid.uuid4()
    obs_uuid = uuid.uuid4()
    obj = _make_obj(
        obj_uuid=obj_uuid,
        obs_uuid=obs_uuid,
        physical_properties={"sep_flux": 1234.5, "sep_a": 3.2},
        mask_rle={"size": [64, 64], "counts": "abc"},
        bounding_box={"x": 10, "y": 20, "w": 40, "h": 30},
    )
    clf = _make_clf()
    session = _session_for(obj, [], clf)

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj_uuid}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["object_uuid"] == str(obj_uuid)
        assert data["source_observation_uuid"] == str(obs_uuid)
        assert data["sky_coordinate_ra_degrees"] == pytest.approx(83.82)
        assert data["sky_coordinate_dec_degrees"] == pytest.approx(-5.39)
        assert data["classified_object_type"] == "spiral_galaxy"
        assert data["catalog_object_name"] == "NGC 1977"
        assert data["catalog_magnitude"] == pytest.approx(8.4)
        assert data["catalog_redshift"] == pytest.approx(0.002)
        assert data["is_anomaly_flagged"] is False
        assert data["physical_properties"] == {"sep_flux": 1234.5, "sep_a": 3.2}
        assert data["segmentation_mask_rle"] == {"size": [64, 64], "counts": "abc"}
        assert data["bounding_box_pixels"] == {"x": 10, "y": 20, "w": 40, "h": 30}
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Cross-matches ordered by angular separation
# ---------------------------------------------------------------------------


def test_object_detail_cross_matches_ordered_by_separation():
    obj = _make_obj()
    match_close = _make_match(catalog="SIMBAD", source_id="SIMBAD_001", separation=0.4)
    match_far = _make_match(catalog="NED", source_id="NED_001", separation=2.1)
    session = _session_for(obj, [match_close, match_far], _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        matches = resp.json()["cross_matches"]
        assert len(matches) == 2
        assert matches[0]["angular_separation_arcseconds"] == pytest.approx(0.4)
        assert matches[0]["catalog_name"] == "SIMBAD"
        assert matches[1]["angular_separation_arcseconds"] == pytest.approx(2.1)
        assert matches[1]["catalog_name"] == "NED"
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# External catalog URLs
# ---------------------------------------------------------------------------


def test_object_detail_simbad_external_url():
    obj = _make_obj()
    match = _make_match(catalog="SIMBAD", source_id="* alf Ori")
    session = _session_for(obj, [match], _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        m = resp.json()["cross_matches"][0]
        assert m["external_url"] is not None
        assert "simbad" in m["external_url"].lower() or "u-strasbg" in m["external_url"]
    finally:
        _teardown(app)


def test_object_detail_ned_external_url():
    obj = _make_obj()
    match = _make_match(catalog="NED", source_id="NGC 4889")
    session = _session_for(obj, [match], _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        m = resp.json()["cross_matches"][0]
        assert m["external_url"] is not None
        assert "ned.ipac" in m["external_url"]
    finally:
        _teardown(app)


def test_object_detail_unknown_catalog_has_null_url():
    obj = _make_obj()
    match = _make_match(catalog="CUSTOM_CATALOG", source_id="XYZ_001")
    session = _session_for(obj, [match], _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        m = resp.json()["cross_matches"][0]
        assert m["external_url"] is None
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Latest classification panel
# ---------------------------------------------------------------------------


def test_object_detail_classification_panel():
    obj = _make_obj()
    clf = _make_clf(
        predicted_type="elliptical_galaxy",
        confidence=0.91,
        model_version="rf_v2.0",
        classified_at=datetime(2026, 7, 15, 12, 0, 0),
    )
    session = _session_for(obj, [], clf)

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        c = resp.json()["latest_classification"]
        assert c is not None
        assert c["predicted_object_type"] == "elliptical_galaxy"
        assert c["classification_confidence_score"] == pytest.approx(0.91)
        assert c["ml_model_version"] == "rf_v2.0"
        assert "2026" in c["classified_at"]
        assert c["is_anomaly_flagged"] is False
        assert c["anomaly_explanation"] is None
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Anomaly explanation alert
# ---------------------------------------------------------------------------


def test_object_detail_anomaly_explanation_present_when_flagged():
    obj = _make_obj(anomaly=True)
    clf = _make_clf(
        anomaly_flagged=True,
        anomaly_score=-0.78,
        anomaly_explanation="ML type 'quasar' disagrees with catalog type 'star'",
    )
    session = _session_for(obj, [], clf)

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_anomaly_flagged"] is True
        c = data["latest_classification"]
        assert c["is_anomaly_flagged"] is True
        assert "disagrees" in c["anomaly_explanation"]
        assert c["anomaly_score"] == pytest.approx(-0.78)
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# No classification (latest_classification is null)
# ---------------------------------------------------------------------------


def test_object_detail_no_classification_returns_null():
    obj = _make_obj()
    session = _session_for(obj, [], None)

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        assert resp.json()["latest_classification"] is None
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Cutout URL
# ---------------------------------------------------------------------------


def test_object_detail_cutout_url_signed_when_prefix_present():
    obj = _make_obj(cutout_prefix="seg/obs1/obj1/")
    session = _session_for(obj, [], _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = "https://minio/signed"
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        assert resp.json()["cutout_url"] == "https://minio/signed"
        mock_s3.return_value.generate_presigned_url.assert_called_once()
    finally:
        _teardown(app)


def test_object_detail_cutout_url_null_when_no_prefix():
    obj = _make_obj(cutout_prefix=None)
    session = _session_for(obj, [], _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = "https://minio/signed"
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        assert resp.json()["cutout_url"] is None
        mock_s3.return_value.generate_presigned_url.assert_not_called()
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Physical properties
# ---------------------------------------------------------------------------


def test_object_detail_physical_properties_included():
    props = {"sep_flux": 4200.0, "sep_a": 5.1, "sep_b": 3.7, "sep_theta": 45.0, "sn_ratio": 22.3}
    obj = _make_obj(physical_properties=props)
    session = _session_for(obj, [], _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        pp = resp.json()["physical_properties"]
        assert pp["sep_flux"] == pytest.approx(4200.0)
        assert pp["sn_ratio"] == pytest.approx(22.3)
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Source observation UUID (for link back to viewer)
# ---------------------------------------------------------------------------


def test_object_detail_source_observation_uuid_present():
    obs_uuid = uuid.uuid4()
    obj = _make_obj(obs_uuid=obs_uuid)
    session = _session_for(obj, [], _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj.object_uuid}")

        assert resp.status_code == 200
        assert resp.json()["source_observation_uuid"] == str(obs_uuid)
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Endpoint registered in OpenAPI spec
# ---------------------------------------------------------------------------


def test_object_detail_endpoint_registered_in_openapi():
    from api.main import app

    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = list(resp.json().get("paths", {}).keys())
    assert any(
        "/api/objects/{" in p and "/classifications" not in p and "/cross-matches" not in p
        for p in paths
    ), f"GET /api/objects/{{uuid}} not found in OpenAPI paths: {paths}"
