"""Tests for cone-search and type-filter API endpoints.

GET /api/objects/search  — cone search + type filter (combinable, paginated)
GET /api/objects/types   — distinct classified_object_type values

Uses FastAPI TestClient with a mock database session dependency and a mock
S3 client (for presigned cutout thumbnail URLs).
"""

import math
import unittest.mock as mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.db.session import get_database_session
from api.routers.objects import router
from shared.models import AstronomicalObject


# ---------------------------------------------------------------------------
# Helpers
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
    name: str = "NGC 1234",
    anomaly: bool = False,
    cutout_prefix: str = None,
    uuid: str = "aaaaaaaa-0000-0000-0000-000000000001",
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


# ---------------------------------------------------------------------------
# /api/objects/search — cone search
# ---------------------------------------------------------------------------

class TestConeSearch:
    # Cone search with no type uses one .filter() call (both bbox conditions combined).
    # Cone search + type uses two chained .filter() calls.

    def _cone_mock(self, objects):
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = objects
        return mock_session

    def test_object_within_radius_is_returned(self):
        obj = _make_obj(ra=10.0, dec=20.0)
        mock_session = self._cone_mock([obj])

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?ra=10.0&dec=20.0&radius_arcsec=60")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["object_uuid"] == "aaaaaaaa-0000-0000-0000-000000000001"

    def test_object_far_outside_radius_is_excluded(self):
        """Object ~200 arcsec away should not appear when radius=60 arcsec."""
        # ra=10.0, dec=20.0 is search centre; object at dec=20.1 is ~360 arcsec away
        obj_far = _make_obj(ra=10.0, dec=20.1, uuid="aaaaaaaa-0000-0000-0000-000000000002")
        obj_near = _make_obj(ra=10.0, dec=20.0, uuid="aaaaaaaa-0000-0000-0000-000000000001")

        # Pre-filter returns both; Python haversine filter should drop the far one
        mock_session = self._cone_mock([obj_near, obj_far])

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?ra=10.0&dec=20.0&radius_arcsec=60")

        assert resp.status_code == 200
        uuids = [r["object_uuid"] for r in resp.json()]
        assert "aaaaaaaa-0000-0000-0000-000000000001" in uuids
        assert "aaaaaaaa-0000-0000-0000-000000000002" not in uuids

    def test_results_ordered_by_angular_separation_ascending(self):
        obj_near = _make_obj(ra=10.0, dec=20.0, uuid="near-0000-0000-0000-000000000001")
        obj_mid = _make_obj(ra=10.0, dec=20.005, uuid="mid-00000-0000-0000-000000000002")

        # Return farther object first to confirm sorting happens in code
        mock_session = self._cone_mock([obj_mid, obj_near])

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?ra=10.0&dec=20.0&radius_arcsec=3600")

        assert resp.status_code == 200
        data = resp.json()
        # Near object (dec=20.0 = 0 sep) must come before mid (dec=20.005)
        assert data[0]["object_uuid"] == "near-0000-0000-0000-000000000001"
        assert data[1]["object_uuid"] == "mid-00000-0000-0000-000000000002"

    def test_empty_result_returns_empty_list_not_404(self):
        mock_session = self._cone_mock([])

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?ra=0.0&dec=0.0&radius_arcsec=1")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_x_total_count_header_present(self):
        obj = _make_obj(ra=10.0, dec=20.0)
        mock_session = self._cone_mock([obj])

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?ra=10.0&dec=20.0&radius_arcsec=60")

        assert "x-total-count" in resp.headers

    def test_pagination_limit_and_offset(self):
        objs = [_make_obj(ra=10.0, dec=20.0, uuid=f"aaa-{i:04d}-0000-0000-000000000000") for i in range(5)]
        mock_session = self._cone_mock(objs)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?ra=10.0&dec=20.0&radius_arcsec=3600&limit=2&offset=0")

        assert resp.status_code == 200
        assert len(resp.json()) <= 2


# ---------------------------------------------------------------------------
# /api/objects/search — type filter
# ---------------------------------------------------------------------------

class TestTypeFilter:
    def test_type_filter_returns_matching_objects(self):
        obj = _make_obj(ra=10.0, dec=20.0, obj_type="elliptical_galaxy")
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [obj]
        mock_session.query.return_value.filter.return_value.count.return_value = 1

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?type=elliptical_galaxy")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["classified_object_type"] == "elliptical_galaxy"

    def test_multi_value_type_filter(self):
        obj1 = _make_obj(ra=10.0, dec=20.0, obj_type="spiral_galaxy", uuid="aaa-0001-0000-0000-000000000000")
        obj2 = _make_obj(ra=11.0, dec=21.0, obj_type="elliptical_galaxy", uuid="aaa-0002-0000-0000-000000000000")
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [obj1, obj2]
        mock_session.query.return_value.filter.return_value.count.return_value = 2

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?type=spiral_galaxy&type=elliptical_galaxy")

        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_type_filter_empty_result_returns_list(self):
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.filter.return_value.count.return_value = 0

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?type=unknown_type")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_type_filter_x_total_count_header(self):
        obj = _make_obj(ra=10.0, dec=20.0, obj_type="star")
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [obj]
        mock_session.query.return_value.filter.return_value.count.return_value = 1

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?type=star")

        assert "x-total-count" in resp.headers


# ---------------------------------------------------------------------------
# /api/objects/search — combined cone + type
# ---------------------------------------------------------------------------

class TestConeAndTypeFilter:
    def test_combined_cone_and_type(self):
        obj = _make_obj(ra=10.0, dec=20.0, obj_type="spiral_galaxy")
        mock_session = mock.MagicMock()
        # Combined cone+type: query().filter(bbox).filter(type_in).all()
        mock_session.query.return_value.filter.return_value.filter.return_value.all.return_value = [obj]

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.get(
                "/api/objects/search?ra=10.0&dec=20.0&radius_arcsec=60&type=spiral_galaxy"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["classified_object_type"] == "spiral_galaxy"


# ---------------------------------------------------------------------------
# /api/objects/search — response shape
# ---------------------------------------------------------------------------

class TestSearchResponseShape:
    def test_response_includes_required_fields(self):
        obj = _make_obj(ra=10.0, dec=20.0, obj_type="star", name="HD 12345",
                        anomaly=True, cutout_prefix="obs/abc123/obj/xyz789/")
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [obj]
        mock_session.query.return_value.filter.return_value.count.return_value = 1

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = "https://minio.example/signed"
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?type=star")

        assert resp.status_code == 200
        item = resp.json()[0]
        assert "object_uuid" in item
        assert "sky_coordinate_ra_degrees" in item
        assert "sky_coordinate_dec_degrees" in item
        assert "classified_object_type" in item
        assert "catalog_object_name" in item
        assert "is_anomaly_flagged" in item
        assert "cutout_thumbnail_url" in item

    def test_cutout_thumbnail_url_is_signed_when_prefix_present(self):
        obj = _make_obj(ra=10.0, dec=20.0, cutout_prefix="seg/obs1/obj1/")
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [obj]
        mock_session.query.return_value.filter.return_value.count.return_value = 1

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = "https://minio/signed-url"
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?type=spiral_galaxy")

        assert resp.status_code == 200
        assert resp.json()[0]["cutout_thumbnail_url"] == "https://minio/signed-url"
        mock_s3.return_value.generate_presigned_url.assert_called_once()

    def test_cutout_thumbnail_url_is_null_when_no_prefix(self):
        obj = _make_obj(ra=10.0, dec=20.0, cutout_prefix=None)
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [obj]
        mock_session.query.return_value.filter.return_value.count.return_value = 1

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = "https://minio/signed-url"
            client = _make_app_with_mock_session(mock_session)
            resp = client.get("/api/objects/search?type=spiral_galaxy")

        assert resp.status_code == 200
        assert resp.json()[0]["cutout_thumbnail_url"] is None
        mock_s3.return_value.generate_presigned_url.assert_not_called()


# ---------------------------------------------------------------------------
# /api/objects/types
# ---------------------------------------------------------------------------

class TestObjectTypes:
    def test_returns_distinct_types(self):
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.distinct.return_value.all.return_value = [
            ("spiral_galaxy",),
            ("elliptical_galaxy",),
            ("star",),
        ]

        client = _make_app_with_mock_session(mock_session)
        resp = client.get("/api/objects/types")

        assert resp.status_code == 200
        types = resp.json()
        assert "spiral_galaxy" in types
        assert "elliptical_galaxy" in types
        assert "star" in types
        assert len(types) == 3

    def test_returns_empty_list_when_no_types(self):
        mock_session = mock.MagicMock()
        mock_session.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        client = _make_app_with_mock_session(mock_session)
        resp = client.get("/api/objects/types")

        assert resp.status_code == 200
        assert resp.json() == []
