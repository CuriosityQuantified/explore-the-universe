"""Neo4j driver singleton and FastAPI dependency.

One driver is created at FastAPI startup (init_driver) and closed on
shutdown (close_driver).  Celery tasks that need Neo4j call get_driver()
directly; it lazily initialises the same singleton if the process has not
already called init_driver.
"""
from __future__ import annotations

import logging
from typing import Generator

from neo4j import Driver, GraphDatabase, Session

from shared.config import settings

logger = logging.getLogger(__name__)

_driver: Driver | None = None

# Uniqueness constraints applied once at startup.
_CONSTRAINTS = [
    (
        "CREATE CONSTRAINT IF NOT EXISTS FOR (o:AstronomicalObject) "
        "REQUIRE o.uuid IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:CatalogEntry) "
        "REQUIRE (c.catalog, c.source_id) IS UNIQUE"
    ),
]


def init_driver() -> None:
    """Create the singleton driver and apply schema constraints."""
    global _driver
    _driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    _driver.verify_connectivity()
    with _driver.session() as s:
        for stmt in _CONSTRAINTS:
            s.run(stmt)
    logger.info("Neo4j driver initialised: %s", settings.neo4j_uri)


def close_driver() -> None:
    """Close the singleton driver (called at FastAPI shutdown)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


def get_driver() -> Driver:
    """Return the singleton driver, initialising lazily if needed."""
    global _driver
    if _driver is None:
        init_driver()
    return _driver


def get_neo4j_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a Neo4j session from the singleton driver."""
    with get_driver().session() as session:
        yield session
