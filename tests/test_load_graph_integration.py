"""Neo4j integration tests for load_graph.

Requires a running Neo4j instance (started by docker-compose in CI).
These tests are discovered by the python-tests CI job (docker stack up,
``pytest -m "not slow" -q``), NOT the offline unit-tests job.

Three objects: one spiral_galaxy with two stars inside its bounding box.
Assertions:
  - 3 AstronomicalObject nodes created
  - 2 CONTAINS edges (galaxy → star1, galaxy → star2)
  - 2 CatalogEntry nodes with correct catalog/source_id
  - Re-running load_graph is idempotent (no duplicate nodes/edges)
"""
from __future__ import annotations

import uuid
from unittest import mock

import pytest

try:
    from neo4j import GraphDatabase

    _neo4j_available = True
except ImportError:
    _neo4j_available = False

from shared.config import settings


def _neo4j_reachable() -> bool:
    if not _neo4j_available:
        return False
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.neo4j_integration,
    pytest.mark.skipif(
        not _neo4j_reachable(),
        reason="Neo4j not reachable — start docker-compose stack to run integration tests",
    ),
]


def _clean_test_nodes(driver, obs_uuid_hex: str):
    """Remove all nodes created for this test observation."""
    with driver.session() as s:
        s.run(
            """
            MATCH (obs:Observation {uuid: $uuid})
            OPTIONAL MATCH (o:AstronomicalObject)-[:OBSERVED_IN]->(obs)
            OPTIONAL MATCH (o)-[:SAME_AS]->(c:CatalogEntry)
            DETACH DELETE obs, o, c
            """,
            uuid=obs_uuid_hex,
        )


def _make_mock_db(obs, objects):
    db = mock.MagicMock()
    db.query.return_value.filter.return_value.first.return_value = obs
    db.query.return_value.filter.return_value.all.return_value = objects
    return db


def _make_observation(obs_uuid):
    obs = mock.MagicMock()
    obs.observation_uuid = obs_uuid
    obs.telescope_name = "JWST"
    obs.ingested_at = "2026-01-01T00:00:00"
    return obs


def _make_object(obj_uuid, obs_uuid, *, obj_type, cx, cy, bbox=None, matches=None):
    obj = mock.MagicMock()
    obj.object_uuid = obj_uuid
    obj.source_observation_uuid = obs_uuid
    obj.sky_coordinate_ra_degrees = 180.0
    obj.sky_coordinate_dec_degrees = 45.0
    obj.classified_object_type = obj_type
    obj.catalog_magnitude = None
    obj.catalog_redshift = None
    obj.is_anomaly_flagged = False
    obj.pixel_centroid_x = cx
    obj.pixel_centroid_y = cy
    obj.bounding_box_pixels = bbox
    obj.catalog_cross_matches = matches or []
    return obj


def _make_catalog_match(catalog, source_id, name=None):
    cm = mock.MagicMock()
    cm.catalog_name = catalog
    cm.catalog_source_id = source_id
    cm.raw_catalog_response = {"name": name} if name else None
    return cm


@pytest.fixture()
def neo4j_driver():
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    yield driver
    driver.close()


def test_load_graph_integration_three_objects(neo4j_driver):
    """Full integration: 1 galaxy + 2 stars → 3 nodes, 2 CONTAINS, 2 CatalogEntry."""
    import api.db.neo4j as neo_mod
    from pipeline.tasks.load_graph import load_graph

    obs_uuid = uuid.uuid4()
    galaxy_uuid = uuid.uuid4()
    star1_uuid = uuid.uuid4()
    star2_uuid = uuid.uuid4()

    galaxy_bbox = {"xmin": 0, "ymin": 0, "xmax": 200, "ymax": 200}
    galaxy = _make_object(
        galaxy_uuid,
        obs_uuid,
        obj_type="spiral_galaxy",
        cx=100.0,
        cy=100.0,
        bbox=galaxy_bbox,
        matches=[_make_catalog_match("NED", "NGC1234", "NGC 1234")],
    )
    star1 = _make_object(
        star1_uuid,
        obs_uuid,
        obj_type="star",
        cx=50.0,
        cy=50.0,
        matches=[_make_catalog_match("SIMBAD", "S001")],
    )
    star2 = _make_object(
        star2_uuid,
        obs_uuid,
        obj_type="star",
        cx=150.0,
        cy=150.0,
    )

    mock_db = _make_mock_db(_make_observation(obs_uuid), [galaxy, star1, star2])
    original_driver = neo_mod._driver
    try:
        _clean_test_nodes(neo4j_driver, obs_uuid.hex)

        with mock.patch("pipeline.tasks.load_graph.SessionLocal", return_value=mock_db):
            neo_mod._driver = neo4j_driver
            result = load_graph.run({"observation_uuid": obs_uuid.hex})

        assert result["nodes_merged"] == 3
        assert result["contains_edges"] == 2
        assert result["catalog_entries_merged"] == 2

        with neo4j_driver.session() as s:
            node_count = s.run(
                "MATCH (o:AstronomicalObject)-[:OBSERVED_IN]->(:Observation {uuid: $uuid}) "
                "RETURN count(o) AS n",
                uuid=obs_uuid.hex,
            ).single()["n"]
            assert node_count == 3

            contains_count = s.run(
                "MATCH (container:AstronomicalObject)-[:CONTAINS]->"
                "(contained:AstronomicalObject), "
                "(container)-[:OBSERVED_IN]->(obs:Observation {uuid: $uuid}), "
                "(contained)-[:OBSERVED_IN]->(obs) "
                "RETURN count(*) AS n",
                uuid=obs_uuid.hex,
            ).single()["n"]
            assert contains_count == 2

            catalog_count = s.run(
                "MATCH (:AstronomicalObject {uuid: $galaxy_uuid})-[:SAME_AS]->(c:CatalogEntry) "
                "RETURN c.catalog AS cat, c.source_id AS sid",
                galaxy_uuid=str(galaxy_uuid),
            ).single()
            assert catalog_count["cat"] == "NED"
            assert catalog_count["sid"] == "NGC1234"

            total_catalog_count = s.run(
                "MATCH (o:AstronomicalObject)-[:SAME_AS]->(:CatalogEntry) "
                "WHERE (o)-[:OBSERVED_IN]->(:Observation {uuid: $uuid}) "
                "RETURN count(*) AS n",
                uuid=obs_uuid.hex,
            ).single()["n"]
            assert total_catalog_count == 2

    finally:
        _clean_test_nodes(neo4j_driver, obs_uuid.hex)
        neo_mod._driver = original_driver


def test_load_graph_integration_idempotent(neo4j_driver):
    """Running load_graph twice must not create duplicate nodes or edges."""
    import api.db.neo4j as neo_mod
    from pipeline.tasks.load_graph import load_graph

    obs_uuid = uuid.uuid4()
    obj_uuid = uuid.uuid4()

    obj = _make_object(
        obj_uuid,
        obs_uuid,
        obj_type="star",
        cx=10.0,
        cy=10.0,
        matches=[_make_catalog_match("SIMBAD", "STAR001")],
    )
    mock_db = _make_mock_db(_make_observation(obs_uuid), [obj])
    original_driver = neo_mod._driver
    try:
        _clean_test_nodes(neo4j_driver, obs_uuid.hex)
        with mock.patch("pipeline.tasks.load_graph.SessionLocal", return_value=mock_db):
            neo_mod._driver = neo4j_driver
            load_graph.run({"observation_uuid": obs_uuid.hex})
            # Run a second time — must still be exactly 1 node
            load_graph.run({"observation_uuid": obs_uuid.hex})

        with neo4j_driver.session() as s:
            node_count = s.run(
                "MATCH (o:AstronomicalObject {uuid: $uuid}) RETURN count(o) AS n",
                uuid=str(obj_uuid),
            ).single()["n"]
            assert node_count == 1

            catalog_count = s.run(
                "MATCH (o:AstronomicalObject {uuid: $uuid})-[:SAME_AS]->(c:CatalogEntry) "
                "RETURN count(c) AS n",
                uuid=str(obj_uuid),
            ).single()["n"]
            assert catalog_count == 1

    finally:
        _clean_test_nodes(neo4j_driver, obs_uuid.hex)
        neo_mod._driver = original_driver
