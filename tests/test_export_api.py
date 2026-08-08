"""Regression suite: Issue #11 — data export API endpoints.

GET /api/objects/{uuid}/export/fits    — stream FITS cutout from MinIO
GET /api/objects/{uuid}/export/csv     — single-row CSV download
GET /api/objects/{uuid}/export/votable — VOTable XML download

All tests are offline — no network, no live DB, no running services required.
Uses FastAPI TestClient with a mock database session dependency and a mock
S3 client (for FITS streaming).
"""

import io
import uuid
import unittest.mock as mock

import pytest
from fastapi.testclient import TestClient

from shared.models import AstronomicalObject, ObjectClassification


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
    ra=83.82,
    dec=-5.39,
    obj_type="spiral_galaxy",
    name="NGC 1977",
    magnitude=8.4,
    redshift=0.002,
    anomaly=False,
    cutout_prefix=None,
):
    obj = mock.MagicMock(spec=AstronomicalObject)
    obj.object_uuid = obj_uuid or uuid.uuid4()
    obj.sky_coordinate_ra_degrees = ra
    obj.sky_coordinate_dec_degrees = dec
    obj.classified_object_type = obj_type
    obj.catalog_object_name = name
    obj.catalog_magnitude = magnitude
    obj.catalog_redshift = redshift
    obj.is_anomaly_flagged = anomaly
    obj.cutout_s3_prefix = cutout_prefix
    return obj


def _make_clf(confidence=0.93, anomaly_score=0.12):
    clf = mock.MagicMock(spec=ObjectClassification)
    clf.classification_confidence_score = confidence
    clf.anomaly_score = anomaly_score
    return clf


def _session_for(obj, latest_clf):
    """Return a mock session that dispatches for export endpoints.

    Export endpoints query AstronomicalObject (.filter().first()) and
    ObjectClassification (.filter().order_by().first()).
    """
    mock_session = mock.MagicMock()

    def query_side_effect(model_class):
        q = mock.MagicMock()
        if model_class is AstronomicalObject:
            q.filter.return_value.first.return_value = obj
        else:  # ObjectClassification
            q.filter.return_value.order_by.return_value.first.return_value = latest_clf
        return q

    mock_session.query.side_effect = query_side_effect
    return mock_session


def _session_not_found():
    """Return a mock session where AstronomicalObject lookup returns None."""
    mock_session = mock.MagicMock()

    def query_side_effect(model_class):
        q = mock.MagicMock()
        if model_class is AstronomicalObject:
            q.filter.return_value.first.return_value = None
        else:
            q.filter.return_value.order_by.return_value.first.return_value = None
        return q

    mock_session.query.side_effect = query_side_effect
    return mock_session


# Minimal FITS bytes (valid FITS header keyword)
MINIMAL_FITS_BYTES = b"SIMPLE  =                    T / FITS STANDARD"


# ---------------------------------------------------------------------------
# FITS export
# ---------------------------------------------------------------------------


def test_fits_export_200_with_content_type():
    """FITS endpoint returns 200 with application/fits content type."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, name="NGC 1977", cutout_prefix=f"obs-uuid/{obj_uuid}")
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.get_object.return_value = {
                "Body": io.BytesIO(MINIMAL_FITS_BYTES)
            }
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj_uuid}/export/fits")

        assert resp.status_code == 200
        assert "application/fits" in resp.headers["content-type"]
    finally:
        _teardown(app)


def test_fits_export_content_disposition_uses_catalog_name():
    """Content-Disposition filename uses catalog_object_name when available."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, name="NGC 1977", cutout_prefix=f"obs-uuid/{obj_uuid}")
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.get_object.return_value = {
                "Body": io.BytesIO(MINIMAL_FITS_BYTES)
            }
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj_uuid}/export/fits")

        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert "NGC 1977.fits" in cd
    finally:
        _teardown(app)


def test_fits_export_filename_falls_back_to_uuid():
    """Content-Disposition filename falls back to UUID when no catalog_object_name."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, name=None, cutout_prefix=f"obs-uuid/{obj_uuid}")
    obj.catalog_object_name = None
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.get_object.return_value = {
                "Body": io.BytesIO(MINIMAL_FITS_BYTES)
            }
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj_uuid}/export/fits")

        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert str(obj_uuid) in cd
    finally:
        _teardown(app)


def test_fits_export_streams_body():
    """FITS endpoint streams the S3 body bytes."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, cutout_prefix=f"obs-uuid/{obj_uuid}")
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.get_object.return_value = {
                "Body": io.BytesIO(MINIMAL_FITS_BYTES)
            }
            client = TestClient(app)
            resp = client.get(f"/api/objects/{obj_uuid}/export/fits")

        assert resp.status_code == 200
        assert resp.content == MINIMAL_FITS_BYTES
    finally:
        _teardown(app)


def test_fits_export_404_for_unknown_uuid():
    """FITS endpoint returns 404 for an unknown UUID."""
    session = _session_not_found()

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{uuid.uuid4()}/export/fits")
        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith("application/json")
    finally:
        _teardown(app)


def test_fits_export_404_when_no_cutout_prefix():
    """FITS endpoint returns 404 with JSON body when object has no cutout_s3_prefix."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, cutout_prefix=None)
    obj.cutout_s3_prefix = None
    session = _session_for(obj, None)

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/fits")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def test_csv_export_200_with_content_type():
    """CSV endpoint returns 200 with text/csv content type."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid)
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"] or "text/plain" in resp.headers["content-type"]
    finally:
        _teardown(app)


def test_csv_export_has_correct_columns():
    """CSV response has the required header row with all 10 columns."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid)
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/csv")
        assert resp.status_code == 200
        lines = resp.text.strip().splitlines()
        assert len(lines) == 2  # header + 1 data row
        headers = lines[0].split(",")
        expected = [
            "uuid", "ra", "dec", "type", "catalog_object_name",
            "catalog_magnitude", "catalog_redshift", "is_anomaly_flagged",
            "classification_confidence_score", "anomaly_score",
        ]
        assert headers == expected
    finally:
        _teardown(app)


def test_csv_export_data_row_matches_object():
    """CSV data row contains the correct values from the object."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(
        obj_uuid=obj_uuid,
        ra=83.82,
        dec=-5.39,
        obj_type="spiral_galaxy",
        name="NGC 1977",
        magnitude=8.4,
        redshift=0.002,
        anomaly=False,
    )
    clf = _make_clf(confidence=0.93, anomaly_score=0.12)
    session = _session_for(obj, clf)

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/csv")
        assert resp.status_code == 200
        lines = resp.text.strip().splitlines()
        data = lines[1].split(",")
        assert data[0] == str(obj_uuid)
        assert float(data[1]) == pytest.approx(83.82)
        assert float(data[2]) == pytest.approx(-5.39)
        assert data[3] == "spiral_galaxy"
        assert data[4] == "NGC 1977"
        assert float(data[5]) == pytest.approx(8.4)
        assert float(data[6]) == pytest.approx(0.002)
        assert data[7] == "False"
        assert float(data[8]) == pytest.approx(0.93)
        assert float(data[9]) == pytest.approx(0.12)
    finally:
        _teardown(app)


def test_csv_export_content_disposition_uses_catalog_name():
    """CSV Content-Disposition uses catalog_object_name when available."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, name="NGC 1977")
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/csv")
        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert "NGC 1977.csv" in cd
    finally:
        _teardown(app)


def test_csv_export_content_disposition_falls_back_to_uuid():
    """CSV Content-Disposition falls back to UUID when catalog_object_name is absent."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, name=None)
    obj.catalog_object_name = None
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/csv")
        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert f"{obj_uuid}.csv" in cd
    finally:
        _teardown(app)


def test_csv_export_404_for_unknown_uuid():
    """CSV endpoint returns 404 for an unknown UUID."""
    session = _session_not_found()

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{uuid.uuid4()}/export/csv")
        assert resp.status_code == 404
    finally:
        _teardown(app)


def test_csv_export_classification_fields_none_when_no_classification():
    """CSV classification fields are empty when no classification exists."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid)
    session = _session_for(obj, None)

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/csv")
        assert resp.status_code == 200
        lines = resp.text.strip().splitlines()
        data = lines[1].split(",")
        # classification_confidence_score and anomaly_score should be empty/None
        assert data[8] == "" or data[8].lower() == "none"
        assert data[9] == "" or data[9].lower() == "none"
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# VOTable export
# ---------------------------------------------------------------------------


def test_votable_export_200_with_content_type():
    """VOTable endpoint returns 200 with application/x-votable+xml content type."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid)
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/votable")
        assert resp.status_code == 200
        assert "application/x-votable+xml" in resp.headers["content-type"]
    finally:
        _teardown(app)


def test_votable_export_parseable_by_astropy():
    """VOTable response content is parseable by astropy.io.votable.parse."""
    import astropy.io.votable

    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid)
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/votable")
        assert resp.status_code == 200
        # Must be parseable without raising
        vot = astropy.io.votable.parse(io.BytesIO(resp.content))
        assert vot is not None
    finally:
        _teardown(app)


def test_votable_export_contains_correct_data():
    """VOTable response contains the expected field values."""
    import astropy.io.votable

    obj_uuid = uuid.uuid4()
    obj = _make_obj(
        obj_uuid=obj_uuid,
        ra=83.82,
        dec=-5.39,
        obj_type="spiral_galaxy",
        name="NGC 1977",
        magnitude=8.4,
        redshift=0.002,
        anomaly=False,
    )
    clf = _make_clf(confidence=0.93, anomaly_score=0.12)
    session = _session_for(obj, clf)

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/votable")
        assert resp.status_code == 200
        vot = astropy.io.votable.parse(io.BytesIO(resp.content))
        table = vot.get_first_table()
        arr = table.array
        assert arr["uuid"][0].decode() == str(obj_uuid) if isinstance(arr["uuid"][0], bytes) else arr["uuid"][0] == str(obj_uuid)
        assert float(arr["ra"][0]) == pytest.approx(83.82)
        assert float(arr["dec"][0]) == pytest.approx(-5.39)
        assert float(arr["classification_confidence_score"][0]) == pytest.approx(0.93)
        assert float(arr["anomaly_score"][0]) == pytest.approx(0.12)
    finally:
        _teardown(app)


def test_votable_export_404_for_unknown_uuid():
    """VOTable endpoint returns 404 for an unknown UUID."""
    session = _session_not_found()

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{uuid.uuid4()}/export/votable")
        assert resp.status_code == 404
    finally:
        _teardown(app)


def test_votable_export_content_disposition_uses_catalog_name():
    """VOTable Content-Disposition uses catalog_object_name when available."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, name="NGC 1977")
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/votable")
        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert "NGC 1977.votable" in cd
    finally:
        _teardown(app)


def test_votable_export_content_disposition_falls_back_to_uuid():
    """VOTable Content-Disposition falls back to UUID when catalog_object_name is absent."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid, name=None)
    obj.catalog_object_name = None
    session = _session_for(obj, _make_clf())

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/votable")
        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert f"{obj_uuid}.votable" in cd
    finally:
        _teardown(app)


# ---------------------------------------------------------------------------
# Classification score population
# ---------------------------------------------------------------------------


def test_classification_scores_populated_from_latest_classification():
    """CSV export populates confidence/anomaly from latest ObjectClassification."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid)
    clf = _make_clf(confidence=0.87, anomaly_score=0.45)
    session = _session_for(obj, clf)

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/csv")
        assert resp.status_code == 200
        lines = resp.text.strip().splitlines()
        data = lines[1].split(",")
        assert float(data[8]) == pytest.approx(0.87)
        assert float(data[9]) == pytest.approx(0.45)
    finally:
        _teardown(app)


def test_classification_scores_none_when_no_classification():
    """CSV export populates None for scores when no ObjectClassification exists."""
    obj_uuid = uuid.uuid4()
    obj = _make_obj(obj_uuid=obj_uuid)
    session = _session_for(obj, None)

    app = _make_app(session)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/objects/{obj_uuid}/export/csv")
        assert resp.status_code == 200
        lines = resp.text.strip().splitlines()
        data = lines[1].split(",")
        assert data[8] == "" or data[8].lower() == "none"
        assert data[9] == "" or data[9].lower() == "none"
    finally:
        _teardown(app)
