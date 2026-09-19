"""Offline validation and response-contract tests for catalog browsing."""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.db.session import get_database_session
from api.routers.catalog import router


@pytest.fixture
def browser():
    session = MagicMock()
    session.scalar.return_value = 13372
    session.execute.return_value.mappings.return_value.all.return_value = [{
        "object_uuid": uuid4(), "catalog_object_name": "M31", "classified_object_type": "galaxy",
        "catalog_magnitude": 3.44, "catalog_redshift": None, "sky_coordinate_ra_degrees": 10.68,
        "sky_coordinate_dec_degrees": 41.27, "has_image": True, "constellation": "And",
    }]
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database_session] = lambda: session
    with TestClient(app) as client:
        yield client, session


def test_catalog_page_contract(browser):
    client, _ = browser
    response = client.get("/api/catalog/objects?limit=25&offset=50")
    assert response.status_code == 200
    page = response.json()
    assert page["total_count"] == 13372
    assert (page["limit"], page["offset"]) == (25, 50)
    assert page["results"][0]["catalog_object_name"] == "M31"
    assert page["results"][0]["has_image"] is True
    assert page["results"][0]["catalog_redshift"] is None


@pytest.mark.parametrize("query", [
    "limit=0", "limit=101", "offset=-1", "sort_by=sql", "sort_order=reverse",
    "hemisphere=east", "has_image=maybe", "magnitude_min=nan", "magnitude_max=inf",
    "magnitude_min=10&magnitude_max=2", "q=" + "a" * 121,
])
def test_invalid_filters_rejected_before_database_query(browser, query):
    client, session = browser
    assert client.get("/api/catalog/objects?" + query).status_code == 422
    session.execute.assert_not_called()
    session.scalar.assert_not_called()
