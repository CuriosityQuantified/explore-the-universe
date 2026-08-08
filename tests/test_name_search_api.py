"""Tests for SIMBAD name-search mode of GET /api/objects/search.

Covers:
- Successful name resolution with local catalog matches (AC1)
- Name resolves but no local objects within 5 arcsec (AC2)
- SIMBAD unreachable → 503 (AC3)
- Name not found in SIMBAD → empty results (AC2 variant)

All tests are OFFLINE: resolve_object_name and get_s3_client are mocked.
"""

import unittest.mock as mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.db.session import get_database_session
from api.routers.objects import router
from shared.models import AstronomicalObject

# ---------------------------------------------------------------------------
# Helpers (mirrors test_search_api.py conventions)
# ---------------------------------------------------------------------------

def _make_app_with_mock_session(mock_session):
    """Return a TestClient wired with a mock DB session override."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database_session] = lambda: mock_session
    return TestClient(app)


def _make_obj(
    ra: float,
    dec: float,
    obj_type: str = "spiral_galaxy",
    name: str = "NGC 1300",
    anomaly: bool = False,
    cutout_prefix: str = None,
    uuid: str = "bbbbbbbb-0000-0000-0000-000000000001",
):
    obj = mock.MagicMock(spec=AstronomicalObject)
    obj.object_uuid = uuid
    obj.sky_coordinate_ra_degrees = ra
    obj.sky_coordinate_dec_degrees = dec
    obj.classified_object_type = obj_type
    obj.catalog_object_name = name
    obj.is_anomaly_flagged = anomaly
    obj.cutout_s3_prefix = cutout_prefix
    return obj


def _mock_session_with_objects(objects):
    """Mock session whose .query().filter().all() returns objects."""
    mock_session = mock.MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = objects
    return mock_session


# ---------------------------------------------------------------------------
# GET /api/objects/search?name=NGC+1300
# ---------------------------------------------------------------------------

class TestNameSearch:

    def test_name_resolves_and_local_match_returned(self):
        """AC1: SIMBAD resolves name → local object within 5 arcsec → returned."""
        # NGC 1300 approximate coords: RA=49.9208, Dec=-19.4112
        resolved_ra = 49.9208
        resolved_dec = -19.4112
        obj = _make_obj(ra=resolved_ra, dec=resolved_dec)
        mock_session = _mock_session_with_objects([obj])

        with (
            mock.patch(
                "api.routers.objects.resolve_object_name",
                return_value=(resolved_ra, resolved_dec, "NGC 1300"),
            ),
            mock.patch("api.routers.objects.get_s3_client") as mock_s3,
        ):
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?name=NGC+1300")

        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert data["resolved_ra"] == pytest.approx(resolved_ra)
        assert data["resolved_dec"] == pytest.approx(resolved_dec)
        assert data["simbad_name"] == "NGC 1300"
        assert len(data["results"]) == 1
        assert data["results"][0]["object_uuid"] == "bbbbbbbb-0000-0000-0000-000000000001"

    def test_name_resolves_but_no_local_match(self):
        """AC2: SIMBAD resolves but no local objects within 5 arcsec → empty results, not 404."""
        resolved_ra = 49.9208
        resolved_dec = -19.4112
        # Object is far away (>5 arcsec)
        obj = _make_obj(ra=resolved_ra + 1.0, dec=resolved_dec + 1.0)
        mock_session = _mock_session_with_objects([obj])

        with (
            mock.patch(
                "api.routers.objects.resolve_object_name",
                return_value=(resolved_ra, resolved_dec, "NGC 1300"),
            ),
            mock.patch("api.routers.objects.get_s3_client") as mock_s3,
        ):
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?name=NGC+1300")

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["resolved_ra"] == pytest.approx(resolved_ra)
        assert data["resolved_dec"] == pytest.approx(resolved_dec)
        assert data["simbad_name"] == "NGC 1300"

    def test_name_not_found_in_simbad(self):
        """AC2 variant: SIMBAD returns None (name not found) → empty results with null coords."""
        mock_session = _mock_session_with_objects([])

        with mock.patch(
            "api.routers.objects.resolve_object_name",
            return_value=None,
        ):
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?name=DOESNOTEXIST+XYZ")

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["resolved_ra"] is None
        assert data["resolved_dec"] is None
        assert data["simbad_name"] is None

    def test_simbad_unreachable_returns_503(self):
        """AC3: SIMBAD raises RuntimeError (unreachable) → 503 with error detail."""
        mock_session = _mock_session_with_objects([])

        with mock.patch(
            "api.routers.objects.resolve_object_name",
            side_effect=RuntimeError("SIMBAD unreachable after 3 retries: connection timeout"),
        ):
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?name=NGC+1300")

        assert resp.status_code == 503
        data = resp.json()
        assert "detail" in data
        assert "temporarily unavailable" in data["detail"]

    def test_multiple_matches_all_returned(self):
        """Multiple local objects within 5 arcsec are all returned."""
        resolved_ra = 49.9208
        resolved_dec = -19.4112
        # Two objects within 5 arcsec (same position = 0 arcsec separation)
        obj1 = _make_obj(ra=resolved_ra, dec=resolved_dec, uuid="bbbbbbbb-0000-0000-0000-000000000001")
        obj2 = _make_obj(ra=resolved_ra, dec=resolved_dec, uuid="bbbbbbbb-0000-0000-0000-000000000002")
        mock_session = _mock_session_with_objects([obj1, obj2])

        with (
            mock.patch(
                "api.routers.objects.resolve_object_name",
                return_value=(resolved_ra, resolved_dec, "NGC 1300"),
            ),
            mock.patch("api.routers.objects.get_s3_client") as mock_s3,
        ):
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?name=NGC+1300")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2

    def test_name_search_response_includes_anomaly_and_type_fields(self):
        """Result items include is_anomaly_flagged and classified_object_type."""
        resolved_ra = 10.0
        resolved_dec = 20.0
        obj = _make_obj(ra=resolved_ra, dec=resolved_dec, obj_type="elliptical_galaxy", anomaly=True)
        mock_session = _mock_session_with_objects([obj])

        with (
            mock.patch(
                "api.routers.objects.resolve_object_name",
                return_value=(resolved_ra, resolved_dec, "M87"),
            ),
            mock.patch("api.routers.objects.get_s3_client") as mock_s3,
        ):
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?name=M87")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["classified_object_type"] == "elliptical_galaxy"
        assert result["is_anomaly_flagged"] is True

    def test_name_search_pagination(self):
        """Pagination parameters limit/offset work for name search."""
        resolved_ra = 10.0
        resolved_dec = 20.0
        objs = [
            _make_obj(ra=resolved_ra, dec=resolved_dec, uuid=f"bbbbbbbb-0000-0000-0000-{i:012d}")
            for i in range(3)
        ]
        mock_session = _mock_session_with_objects(objs)

        with (
            mock.patch(
                "api.routers.objects.resolve_object_name",
                return_value=(resolved_ra, resolved_dec, "SomeName"),
            ),
            mock.patch("api.routers.objects.get_s3_client") as mock_s3,
        ):
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?name=SomeName&limit=2&offset=0")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2
        assert resp.headers["x-total-count"] == "3"

    def test_name_search_offset_beyond_results(self):
        """Offset beyond total count returns empty results."""
        resolved_ra = 10.0
        resolved_dec = 20.0
        obj = _make_obj(ra=resolved_ra, dec=resolved_dec)
        mock_session = _mock_session_with_objects([obj])

        with (
            mock.patch(
                "api.routers.objects.resolve_object_name",
                return_value=(resolved_ra, resolved_dec, "SomeName"),
            ),
            mock.patch("api.routers.objects.get_s3_client") as mock_s3,
        ):
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?name=SomeName&limit=10&offset=99")

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert resp.headers["x-total-count"] == "1"
