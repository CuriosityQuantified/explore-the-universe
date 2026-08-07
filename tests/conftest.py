"""Shared pytest fixtures for the offline test suite.

Any test that brings up the FastAPI app via TestClient will trigger the
lifespan, which calls init_driver().  Without a live Neo4j instance that
fails immediately.  The neo4j_mock_lifecycle autouse fixture patches
init_driver / close_driver globally so offline tests are hermetic.

Integration tests that need a live Neo4j (test_load_graph_integration.py)
should be marked ``neo4j_integration``; the fixture yields without patching
for those tests.
"""
from __future__ import annotations

from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _mock_neo4j_lifecycle(request):
    """Patch Neo4j driver lifecycle for tests that don't need a live instance."""
    # neo4j_integration: live Neo4j required (docker stack)
    # neo4j_unit: test exercises neo4j module internals directly — no app lifespan
    if request.node.get_closest_marker(
        "neo4j_integration"
    ) or request.node.get_closest_marker("neo4j_unit"):
        yield
        return

    with (
        mock.patch("api.db.neo4j.init_driver"),
        mock.patch("api.db.neo4j.close_driver"),
    ):
        yield
