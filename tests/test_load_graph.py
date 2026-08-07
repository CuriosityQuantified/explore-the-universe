"""Offline unit tests for pipeline/tasks/load_graph.py and api/db/neo4j.py.

These tests are PURE unit tests — no live Neo4j, no Docker, no network.
They mock the neo4j driver and PostgreSQL session exactly as the rest of
the offline suite does (see test_classification_schema.py for the pattern).
"""
from __future__ import annotations

import inspect
import uuid
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# api/db/neo4j.py tests
# ---------------------------------------------------------------------------


def test_neo4j_module_importable():
    from api.db.neo4j import (  # noqa: F401
        close_driver,
        get_driver,
        get_neo4j_session,
        init_driver,
    )


def test_get_neo4j_session_is_generator():
    """get_neo4j_session must be a generator function so FastAPI Depends works."""
    from api.db.neo4j import get_neo4j_session

    assert inspect.isgeneratorfunction(get_neo4j_session)


@pytest.mark.neo4j_unit
def test_init_driver_creates_driver_and_applies_constraints():
    import api.db.neo4j as neo_mod

    mock_session = mock.MagicMock()
    mock_driver = mock.MagicMock()
    mock_driver.session.return_value.__enter__ = mock.Mock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = mock.Mock(return_value=False)

    original_driver = neo_mod._driver
    try:
        with mock.patch("api.db.neo4j.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver
            neo_mod._driver = None
            neo_mod.init_driver()

        assert neo_mod._driver is mock_driver
        mock_driver.verify_connectivity.assert_called_once()
        # Both constraints should be run
        assert mock_session.run.call_count == 2
        calls = [c.args[0] for c in mock_session.run.call_args_list]
        assert any("AstronomicalObject" in c for c in calls)
        assert any("CatalogEntry" in c for c in calls)
    finally:
        neo_mod._driver = original_driver


@pytest.mark.neo4j_unit
def test_close_driver_nils_module_state():
    import api.db.neo4j as neo_mod

    mock_driver = mock.MagicMock()
    original_driver = neo_mod._driver
    try:
        neo_mod._driver = mock_driver
        neo_mod.close_driver()
        assert neo_mod._driver is None
        mock_driver.close.assert_called_once()
    finally:
        neo_mod._driver = original_driver


@pytest.mark.neo4j_unit
def test_get_driver_lazily_initialises():
    import api.db.neo4j as neo_mod

    mock_driver = mock.MagicMock()
    mock_driver.session.return_value.__enter__ = mock.Mock(return_value=mock.MagicMock())
    mock_driver.session.return_value.__exit__ = mock.Mock(return_value=False)

    original_driver = neo_mod._driver
    try:
        neo_mod._driver = None
        with mock.patch("api.db.neo4j.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver
            returned = neo_mod.get_driver()
        assert returned is mock_driver
    finally:
        neo_mod._driver = original_driver


def test_main_app_has_lifespan():
    """api/main.py must wire init_driver/close_driver via a lifespan context."""
    import api.main as main_mod

    src = inspect.getsource(main_mod)
    assert "lifespan" in src, "main.py must use a lifespan context manager"
    assert "init_driver" in src, "lifespan must call init_driver()"
    assert "close_driver" in src, "lifespan must call close_driver()"


# ---------------------------------------------------------------------------
# pipeline/tasks/load_graph.py — import & source checks
# ---------------------------------------------------------------------------


def test_load_graph_importable():
    from pipeline.tasks.load_graph import load_graph  # noqa: F401


def test_load_graph_uses_unwind():
    from pipeline.tasks.load_graph import load_graph

    src = inspect.getsource(load_graph)
    assert "UNWIND" in src, "load_graph must use UNWIND batching, not per-object Cypher"


def test_load_graph_uses_merge():
    from pipeline.tasks.load_graph import load_graph

    src = inspect.getsource(load_graph)
    assert "MERGE" in src, "load_graph must use MERGE for idempotent upserts"


def test_load_graph_covers_all_relationship_types():
    from pipeline.tasks import load_graph as lg_mod

    src = inspect.getsource(lg_mod)
    for rel in ("SAME_AS", "OBSERVED_IN", "CONTAINS"):
        assert rel in src, f"load_graph must create {rel} relationships"


def test_load_graph_container_types_match_spec():
    from pipeline.tasks.load_graph import _CONTAINER_TYPES

    required = {
        "spiral_galaxy",
        "elliptical_galaxy",
        "irregular_galaxy",
        "lenticular_galaxy",
        "globular_cluster",
    }
    assert required == set(_CONTAINER_TYPES)


def test_in_bbox_true_when_centroid_inside():
    from pipeline.tasks.load_graph import _in_bbox

    bbox = {"xmin": 10, "ymin": 20, "xmax": 50, "ymax": 60}
    assert _in_bbox(30, 40, bbox) is True


def test_in_bbox_false_when_centroid_outside():
    from pipeline.tasks.load_graph import _in_bbox

    bbox = {"xmin": 10, "ymin": 20, "xmax": 50, "ymax": 60}
    assert _in_bbox(5, 40, bbox) is False
    assert _in_bbox(30, 70, bbox) is False


def test_in_bbox_edge_on_boundary():
    from pipeline.tasks.load_graph import _in_bbox

    bbox = {"xmin": 10, "ymin": 10, "xmax": 50, "ymax": 50}
    assert _in_bbox(10, 10, bbox) is True
    assert _in_bbox(50, 50, bbox) is True


# ---------------------------------------------------------------------------
# load_graph task — mock DB + mock Neo4j driver (no docker)
# ---------------------------------------------------------------------------


def _make_observation(obs_uuid):
    obs = mock.MagicMock()
    obs.observation_uuid = obs_uuid
    obs.telescope_name = "JWST"
    obs.ingested_at = "2026-01-01T00:00:00"
    return obs


def _make_object(
    obj_uuid,
    obs_uuid,
    *,
    obj_type="star",
    cx=None,
    cy=None,
    bbox=None,
    catalog_matches=None,
):
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
    obj.catalog_cross_matches = catalog_matches or []
    return obj


def _make_catalog_match(catalog="SIMBAD", source_id="M31", name="Andromeda"):
    cm = mock.MagicMock()
    cm.catalog_name = catalog
    cm.catalog_source_id = source_id
    cm.raw_catalog_response = {"name": name}
    return cm


def _run_load_graph_with_mocks(obs_uuid, objects, mock_neo_session):
    """Helper: patch SessionLocal + get_driver, call load_graph.run()."""
    from pipeline.tasks.load_graph import load_graph

    obs = _make_observation(obs_uuid)

    mock_db = mock.MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = obs
    mock_db.query.return_value.filter.return_value.all.return_value = objects

    mock_driver = mock.MagicMock()
    mock_driver.session.return_value.__enter__ = mock.Mock(
        return_value=mock_neo_session
    )
    mock_driver.session.return_value.__exit__ = mock.Mock(return_value=False)

    with (
        mock.patch("pipeline.tasks.load_graph.SessionLocal", return_value=mock_db),
        mock.patch("pipeline.tasks.load_graph.get_driver", return_value=mock_driver),
    ):
        return load_graph.run({"observation_uuid": obs_uuid.hex})


def test_load_graph_merges_object_nodes():
    obs_uuid = uuid.uuid4()
    obj_uuid = uuid.uuid4()
    obj = _make_object(obj_uuid, obs_uuid, obj_type="star")

    neo_session = mock.MagicMock()
    result = _run_load_graph_with_mocks(obs_uuid, [obj], neo_session)

    assert result["nodes_merged"] == 1
    assert result["observation_uuid"] == obs_uuid.hex
    cypher_calls = [c.args[0] for c in neo_session.run.call_args_list]
    assert any("UNWIND" in c and "AstronomicalObject" in c for c in cypher_calls)


def test_load_graph_creates_catalog_entries():
    obs_uuid = uuid.uuid4()
    obj_uuid = uuid.uuid4()
    cm = _make_catalog_match()
    obj = _make_object(obj_uuid, obs_uuid, catalog_matches=[cm])

    neo_session = mock.MagicMock()
    result = _run_load_graph_with_mocks(obs_uuid, [obj], neo_session)

    assert result["catalog_entries_merged"] == 1
    cypher_calls = [c.args[0] for c in neo_session.run.call_args_list]
    assert any("CatalogEntry" in c and "SAME_AS" in c for c in cypher_calls)


def test_load_graph_creates_observed_in_edges():
    obs_uuid = uuid.uuid4()
    obj_uuid = uuid.uuid4()
    obj = _make_object(obj_uuid, obs_uuid)

    neo_session = mock.MagicMock()
    _run_load_graph_with_mocks(obs_uuid, [obj], neo_session)

    cypher_calls = [c.args[0] for c in neo_session.run.call_args_list]
    assert any("OBSERVED_IN" in c for c in cypher_calls)


def test_load_graph_contains_inference():
    """Galaxy CONTAINS two stars whose centroids are inside its bbox."""
    obs_uuid = uuid.uuid4()
    galaxy_uuid = uuid.uuid4()
    star1_uuid = uuid.uuid4()
    star2_uuid = uuid.uuid4()

    galaxy_bbox = {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 100}
    galaxy = _make_object(
        galaxy_uuid,
        obs_uuid,
        obj_type="spiral_galaxy",
        cx=50.0,
        cy=50.0,
        bbox=galaxy_bbox,
    )
    star1 = _make_object(star1_uuid, obs_uuid, obj_type="star", cx=30.0, cy=40.0)
    star2 = _make_object(star2_uuid, obs_uuid, obj_type="star", cx=70.0, cy=60.0)

    neo_session = mock.MagicMock()
    result = _run_load_graph_with_mocks(
        obs_uuid, [galaxy, star1, star2], neo_session
    )

    assert result["contains_edges"] == 2
    cypher_calls = [c.args[0] for c in neo_session.run.call_args_list]
    assert any("CONTAINS" in c for c in cypher_calls)


def test_load_graph_no_contains_when_centroid_outside():
    obs_uuid = uuid.uuid4()
    galaxy_uuid = uuid.uuid4()
    star_uuid = uuid.uuid4()

    galaxy_bbox = {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}
    galaxy = _make_object(
        galaxy_uuid,
        obs_uuid,
        obj_type="elliptical_galaxy",
        cx=5.0,
        cy=5.0,
        bbox=galaxy_bbox,
    )
    # Star is outside the galaxy bbox
    star = _make_object(star_uuid, obs_uuid, obj_type="star", cx=200.0, cy=200.0)

    neo_session = mock.MagicMock()
    result = _run_load_graph_with_mocks(obs_uuid, [galaxy, star], neo_session)

    assert result["contains_edges"] == 0


def test_load_graph_idempotent_uses_merge_not_create():
    """Source check: load_graph must not use CREATE for nodes (only MERGE)."""
    import pipeline.tasks.load_graph as lg_mod

    src = inspect.getsource(lg_mod)
    # Raw CREATE (node creation) should not appear; MERGE is required
    # Allow "CREATE CONSTRAINT" in the constraints module, but not in load_graph
    lines_with_create = [
        ln for ln in src.splitlines() if "CREATE " in ln and "CONSTRAINT" not in ln
    ]
    assert not lines_with_create, (
        "load_graph must use MERGE, not CREATE, for idempotent node writes"
    )


def test_ingest_chain_has_10_tasks():
    from pipeline.tasks.ingest import ingest_observation

    src = inspect.getsource(ingest_observation)
    assert "load_graph.s()" in src, "ingest chain must include load_graph.s()"
    for task_name in (
        "validate_wcs.s()",
        "generate_tiles.s()",
        "detect_sources.s()",
        "segment_sam.s()",
        "generate_cutouts.s()",
        "cross_match_catalogs.s()",
        "classify_objects.s()",
        "detect_anomalies.s()",
        "load_graph.s()",
    ):
        assert task_name in src, f"Missing {task_name!r} in ingest_observation chain"
