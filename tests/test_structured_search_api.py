"""Tests for structured query API endpoint.

POST /api/objects/search — structured filter query (magnitude, redshift, anomaly, type, obs, sort, pagination)

Uses FastAPI TestClient with a mock database session dependency and a mock
S3 client (for presigned cutout thumbnail URLs).

Mock strategy for SQLAlchemy chaining:
  Each .filter() or .order_by() call returns the same mock query object,
  so we configure the terminal methods (count / all) on the deepest returnable.
"""

import uuid
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
    ra: float = 10.0,
    dec: float = 20.0,
    obj_type: str = "spiral_galaxy",
    name: str = "NGC 1234",
    anomaly: bool = False,
    cutout_prefix: str = None,
    uuid_str: str = "aaaaaaaa-0000-0000-0000-000000000001",
    magnitude: float = 15.0,
    redshift: float = 0.05,
    obs_uuid: str = "bbbbbbbb-0000-0000-0000-000000000001",
):
    obj = mock.MagicMock(spec=AstronomicalObject)
    obj.object_uuid = uuid_str
    obj.sky_coordinate_ra_degrees = ra
    obj.sky_coordinate_dec_degrees = dec
    obj.classified_object_type = obj_type
    obj.catalog_object_name = name
    obj.is_anomaly_flagged = anomaly
    obj.cutout_s3_prefix = cutout_prefix
    obj.catalog_magnitude = magnitude
    obj.catalog_redshift = redshift
    obj.source_observation_uuid = uuid.UUID(obs_uuid)
    return obj


def _make_chained_mock(objects, count=None):
    """Return a mock session where all query chain methods resolve properly.

    The structured search endpoint chains:
      .query(...).filter(...).filter(...) ... .order_by(...).count()
      .query(...).filter(...).filter(...) ... .order_by(...).offset(...).limit(...).all()

    We make the MagicMock return itself for all chaining methods so any
    combination of filters terminates correctly.
    """
    mock_session = mock.MagicMock()
    mock_query = mock.MagicMock()

    # The chain: session.query(...) → mock_query
    mock_session.query.return_value = mock_query

    # Every chaining call returns the same mock_query object
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query

    # Terminal methods
    mock_query.count.return_value = count if count is not None else len(objects)
    mock_query.all.return_value = objects

    return mock_session


# ---------------------------------------------------------------------------
# TestStructuredSearch
# ---------------------------------------------------------------------------

class TestStructuredSearch:

    # ------------------------------------------------------------------
    # 1. POST returns 200 with results and total_count
    # ------------------------------------------------------------------

    def test_post_returns_200_with_results_and_total_count(self):
        obj = _make_obj()
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "total_count" in data
        assert isinstance(data["results"], list)
        assert isinstance(data["total_count"], int)

    # ------------------------------------------------------------------
    # 2. Empty body (all filters optional) returns results
    # ------------------------------------------------------------------

    def test_empty_body_returns_results(self):
        obj = _make_obj()
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["object_uuid"] == "aaaaaaaa-0000-0000-0000-000000000001"

    # ------------------------------------------------------------------
    # 3. type filter — single value
    # ------------------------------------------------------------------

    def test_single_type_filter(self):
        obj = _make_obj(obj_type="elliptical_galaxy")
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"type": ["elliptical_galaxy"]})

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["classified_object_type"] == "elliptical_galaxy"

    # ------------------------------------------------------------------
    # 3b. type filter — multi-value (OR within list)
    # ------------------------------------------------------------------

    def test_multi_value_type_filter(self):
        obj1 = _make_obj(obj_type="spiral_galaxy", uuid_str="aaa-0001-0000-0000-000000000000")
        obj2 = _make_obj(obj_type="elliptical_galaxy", uuid_str="aaa-0002-0000-0000-000000000000")
        mock_session = _make_chained_mock([obj1, obj2], count=2)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"type": ["spiral_galaxy", "elliptical_galaxy"]},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2
        types = {r["classified_object_type"] for r in data["results"]}
        assert types == {"spiral_galaxy", "elliptical_galaxy"}

    # ------------------------------------------------------------------
    # 4. magnitude_min and magnitude_max — both bounds inclusive
    # ------------------------------------------------------------------

    def test_magnitude_min_filter(self):
        obj = _make_obj(magnitude=18.0)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"magnitude_min": 15.0})

        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    def test_magnitude_max_filter(self):
        obj = _make_obj(magnitude=10.0)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"magnitude_max": 12.0})

        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    def test_magnitude_range_both_bounds(self):
        obj = _make_obj(magnitude=14.5)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"magnitude_min": 14.0, "magnitude_max": 15.0},
            )

        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    # ------------------------------------------------------------------
    # 5. redshift_max filter
    # ------------------------------------------------------------------

    def test_redshift_max_filter(self):
        obj = _make_obj(redshift=0.03)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"redshift_max": 0.1})

        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    # ------------------------------------------------------------------
    # 5b. redshift_min filter
    # ------------------------------------------------------------------

    def test_redshift_min_filter(self):
        obj = _make_obj(redshift=0.5)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"redshift_min": 0.3})

        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    def test_redshift_min_and_max_filter(self):
        obj = _make_obj(redshift=0.4)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search", json={"redshift_min": 0.2, "redshift_max": 0.6}
            )

        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    # ------------------------------------------------------------------
    # 6. is_anomaly: true filters to only flagged objects
    # ------------------------------------------------------------------

    def test_is_anomaly_true_filter(self):
        obj = _make_obj(anomaly=True)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"is_anomaly": True})

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert data["results"][0]["is_anomaly_flagged"] is True

    def test_is_anomaly_false_filter(self):
        obj = _make_obj(anomaly=False)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"is_anomaly": False})

        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    # ------------------------------------------------------------------
    # 7. observation_uuid scopes to one observation
    # ------------------------------------------------------------------

    def test_observation_uuid_filter(self):
        obs_id = "cccccccc-0000-0000-0000-000000000001"
        obj = _make_obj(obs_uuid=obs_id)
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"observation_uuid": obs_id})

        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    def test_observation_uuid_invalid_returns_422(self):
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"observation_uuid": "not-a-uuid"},
            )

        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # 8. Combined filters AND together
    # ------------------------------------------------------------------

    def test_combined_filters_and_together(self):
        obs_id = "dddddddd-0000-0000-0000-000000000001"
        obj = _make_obj(
            obj_type="quasar",
            anomaly=True,
            magnitude=19.0,
            redshift=0.8,
            obs_uuid=obs_id,
        )
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={
                    "type": ["quasar"],
                    "is_anomaly": True,
                    "magnitude_min": 18.0,
                    "redshift_max": 1.0,
                    "observation_uuid": obs_id,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert data["results"][0]["classified_object_type"] == "quasar"

    # ------------------------------------------------------------------
    # 9. Response has total_count field in JSON body
    # ------------------------------------------------------------------

    def test_total_count_in_json_body(self):
        objs = [_make_obj(uuid_str=f"aaa-{i:04d}-0000-0000-000000000001") for i in range(5)]
        mock_session = _make_chained_mock(objs, count=5)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert data["total_count"] == 5

    def test_x_total_count_header_present(self):
        obj = _make_obj()
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={})

        assert "x-total-count" in resp.headers
        assert resp.headers["x-total-count"] == "1"

    # ------------------------------------------------------------------
    # 10. Sort by magnitude asc/desc
    # ------------------------------------------------------------------

    def test_sort_by_magnitude_asc(self):
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"sort_by": "magnitude", "sort_order": "asc"},
            )

        assert resp.status_code == 200

    def test_sort_by_magnitude_desc(self):
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"sort_by": "magnitude", "sort_order": "desc"},
            )

        assert resp.status_code == 200

    def test_sort_by_type(self):
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"sort_by": "type", "sort_order": "asc"},
            )

        assert resp.status_code == 200

    def test_sort_by_angular_separation_falls_back_gracefully(self):
        """angular_separation sort in pure-filter mode falls back to magnitude sort — still 200."""
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"sort_by": "angular_separation"},
            )

        assert resp.status_code == 200

    def test_invalid_sort_by_returns_422(self):
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"sort_by": "invalid_field"},
            )

        assert resp.status_code == 422

    def test_invalid_sort_order_returns_422(self):
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/objects/search",
                json={"sort_order": "random"},
            )

        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # 11. Pagination — limit + offset
    # ------------------------------------------------------------------

    def test_pagination_limit(self):
        """Endpoint accepts limit param without error."""
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"limit": 10, "offset": 0})

        assert resp.status_code == 200

    def test_pagination_offset(self):
        """Endpoint accepts offset param without error."""
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"limit": 5, "offset": 10})

        assert resp.status_code == 200

    def test_pagination_total_count_reflects_full_count_not_page(self):
        """total_count is the unsliced count (from .count()), not len(results)."""
        page_objs = [_make_obj(uuid_str=f"aaa-{i:04d}-0000-0000-000000000001") for i in range(5)]
        # Simulate 100 total objects but only 5 on this page
        mock_session = _make_chained_mock(page_objs, count=100)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"limit": 5, "offset": 0})

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 100
        assert len(data["results"]) == 5

    def test_limit_out_of_range_returns_422(self):
        """limit=0 is below minimum (ge=1) and should return 422."""
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"limit": 0})

        assert resp.status_code == 422

    def test_limit_max_boundary_accepted(self):
        """limit=500 (maximum) should be accepted."""
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={"limit": 500})

        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # 12. Results shape — ObjectSearchResponse fields present
    # ------------------------------------------------------------------

    def test_result_item_has_expected_fields(self):
        obj = _make_obj()
        mock_session = _make_chained_mock([obj], count=1)

        with mock.patch("api.routers.objects.get_s3_client") as mock_s3:
            mock_s3.return_value.generate_presigned_url.return_value = None
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={})

        assert resp.status_code == 200
        item = resp.json()["results"][0]
        for field in (
            "object_uuid",
            "sky_coordinate_ra_degrees",
            "sky_coordinate_dec_degrees",
            "classified_object_type",
            "catalog_object_name",
            "is_anomaly_flagged",
            "cutout_thumbnail_url",
        ):
            assert field in item, f"Missing field: {field}"

    # ------------------------------------------------------------------
    # 13. Empty results — returns 200 with empty list and total_count 0
    # ------------------------------------------------------------------

    def test_empty_results_returns_200_not_404(self):
        mock_session = _make_chained_mock([], count=0)

        with mock.patch("api.routers.objects.get_s3_client"):
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/objects/search", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["total_count"] == 0
