"""Exercise catalog SQL against PostgreSQL; fixture data is rolled back."""
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.db.session import engine, get_database_session
from api.routers.catalog import router
from pipeline.catalog import normalize_name
from shared.models import AstronomicalObject, Observation


@pytest.fixture
def catalog():
    prefix = "browse" + uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection) as session:
            observation = Observation(archive_observation_id=prefix, telescope_name="test", instrument_name="test")
            session.add(observation)
            session.flush()
            specs = [
                ("Alpha", "galaxy", 3, 0, "image/a", [normalize_name(prefix + " Andromeda")]),
                ("Beta", "galaxy", 8, -20, None, None),
                ("Gamma", "nebula", None, 30, "", "legacy non-array"),
                ("Literal%_", "nebula", 8, -30, "image/d", []),
            ]
            for index, (name, kind, magnitude, dec, image, aliases) in enumerate(specs):
                session.add(AstronomicalObject(
                    source_observation_uuid=observation.observation_uuid,
                    catalog_object_name=prefix + name, classified_object_type=kind,
                    catalog_magnitude=magnitude, catalog_redshift=index / 100,
                    sky_coordinate_ra_degrees=index * 10, sky_coordinate_dec_degrees=dec,
                    cutout_s3_prefix=image, physical_properties={"aliases": aliases},
                ))
            session.flush()
            app = FastAPI()
            app.include_router(router)
            app.dependency_overrides[get_database_session] = lambda: session
            with TestClient(app) as client:
                def search(**params):
                    response = client.get("/api/catalog/objects", params={"q": prefix, **params})
                    assert response.status_code == 200, response.text
                    return response.json()
                yield search, prefix
        transaction.rollback()


def names(page, prefix):
    return [row["catalog_object_name"].removeprefix(prefix) for row in page["results"]]


def test_pagination_and_sorting(catalog):
    search, prefix = catalog
    first = search(limit=2)
    second = search(limit=2, offset=2)
    assert first["total_count"] == second["total_count"] == 4
    assert names(first, prefix) == ["Alpha", "Beta"]
    assert names(second, prefix) == ["Gamma", "Literal%_"]
    assert search(offset=4)["results"] == []
    assert names(search(sort_by="magnitude"), prefix) == ["Alpha", "Beta", "Literal%_", "Gamma"]
    assert names(search(sort_by="magnitude", sort_order="desc"), prefix) == ["Beta", "Literal%_", "Alpha", "Gamma"]
    for sort_by in ("name", "type", "redshift", "ra", "dec"):
        page = search(sort_by=sort_by, sort_order="desc")
        assert len(page["results"]) == 4
    assert names(search(sort_by="ra", sort_order="desc"), prefix)[0] == "Literal%_"


def test_combined_filters_and_empty_images(catalog):
    search, prefix = catalog
    assert names(search(type="galaxy", hemisphere="north", has_image="true", magnitude_min=3, magnitude_max=3), prefix) == ["Alpha"]
    assert names(search(has_image="false"), prefix) == ["Beta", "Gamma"]
    assert names(search(hemisphere="south"), prefix) == ["Beta", "Literal%_"]
    assert search(type="galaxy", magnitude_min=9)["total_count"] == 0


def test_aliases_and_literal_wildcards(catalog):
    search, prefix = catalog
    assert names(search(q=prefix + " Andro"), prefix) == ["Alpha"]
    assert names(search(q=prefix + "Literal%_"), prefix) == ["Literal%_"]
    assert search(q=prefix + "missing%")["total_count"] == 0
