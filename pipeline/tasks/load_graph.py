"""Bulk-load observation objects into the Neo4j knowledge graph.

Tenth (final) step in the 10-task pipeline chain.  Idempotently MERGEs
all AstronomicalObject nodes for an observation, creates CatalogEntry
nodes linked via SAME_AS, links each object to its Observation via
OBSERVED_IN, and infers CONTAINS edges where a smaller object's pixel
centroid falls inside a galaxy/cluster's bounding box.

Containment uses PostgreSQL bounding-box pixel conventions — no Neo4j
spatial.  Galaxy types eligible to CONTAIN other objects:
  spiral_galaxy, elliptical_galaxy, irregular_galaxy,
  lenticular_galaxy, globular_cluster.

Batching: all Cypher writes use UNWIND so a single transaction covers
the full observation rather than one round-trip per object.
"""
from __future__ import annotations

import logging
import uuid as _uuid

from api.db.neo4j import get_driver
from api.db.session import SessionLocal
from pipeline.celery_app import celery_app
from shared.models import AstronomicalObject, Observation

logger = logging.getLogger(__name__)

_CONTAINER_TYPES = frozenset(
    {
        "spiral_galaxy",
        "elliptical_galaxy",
        "irregular_galaxy",
        "lenticular_galaxy",
        "globular_cluster",
    }
)


def _in_bbox(cx: float, cy: float, bbox: dict) -> bool:
    """Return True if pixel (cx, cy) lies inside bbox {xmin,ymin,xmax,ymax}."""
    return (
        bbox.get("xmin", 1) <= cx <= bbox.get("xmax", -1)
        and bbox.get("ymin", 1) <= cy <= bbox.get("ymax", -1)
    )


@celery_app.task(bind=True, acks_late=True)
def load_graph(self, prev_result: dict) -> dict:
    """MERGE all objects for an observation into the Neo4j knowledge graph.

    Args:
        prev_result: Result dict from detect_anomalies; must contain
            ``observation_uuid`` (hex string).

    Returns:
        Dict with observation_uuid, nodes_merged, catalog_entries_merged,
        contains_edges, and status.
    """
    observation_uuid_hex = prev_result.get("observation_uuid")
    if not observation_uuid_hex:
        raise ValueError("load_graph: prev_result must contain 'observation_uuid'")

    observation_uuid = _uuid.UUID(observation_uuid_hex)

    db = SessionLocal()
    try:
        observation = (
            db.query(Observation)
            .filter(Observation.observation_uuid == observation_uuid)
            .first()
        )
        if observation is None:
            raise ValueError(f"Observation {observation_uuid_hex} not found")

        objects = (
            db.query(AstronomicalObject)
            .filter(AstronomicalObject.source_observation_uuid == observation_uuid)
            .all()
        )

        # --- build payloads while the session is open ---

        object_rows = [
            {
                "uuid": str(obj.object_uuid),
                "ra": obj.sky_coordinate_ra_degrees,
                "dec": obj.sky_coordinate_dec_degrees,
                "type": obj.classified_object_type,
                "magnitude": obj.catalog_magnitude,
                "redshift": obj.catalog_redshift,
                "is_anomaly": bool(obj.is_anomaly_flagged),
            }
            for obj in objects
        ]

        catalog_rows: list[dict] = []
        for obj in objects:
            for cm in obj.catalog_cross_matches:
                raw_response = (
                    cm.raw_catalog_response
                    if isinstance(cm.raw_catalog_response, dict)
                    else {}
                )
                name = (
                    raw_response.get("name")
                    or raw_response.get("main_id")
                    or raw_response.get("object_name")
                    or cm.catalog_source_id
                )
                catalog_rows.append(
                    {
                        "object_uuid": str(obj.object_uuid),
                        "catalog": cm.catalog_name,
                        "source_id": cm.catalog_source_id,
                        "name": name,
                    }
                )

        # Infer CONTAINS: object A is contained by container B when A's
        # pixel centroid lies inside B's bounding_box_pixels and B is a
        # galaxy / globular cluster.
        containers = [
            o
            for o in objects
            if o.classified_object_type in _CONTAINER_TYPES
            and o.bounding_box_pixels is not None
        ]
        contains_pairs: list[dict] = []
        for obj in objects:
            if obj.pixel_centroid_x is None or obj.pixel_centroid_y is None:
                continue
            for container in containers:
                if container.object_uuid == obj.object_uuid:
                    continue
                if _in_bbox(
                    obj.pixel_centroid_x,
                    obj.pixel_centroid_y,
                    container.bounding_box_pixels,
                ):
                    contains_pairs.append(
                        {
                            "container_uuid": str(container.object_uuid),
                            "contained_uuid": str(obj.object_uuid),
                        }
                    )

        obs_telescope = observation.telescope_name
        obs_ingested_at = str(observation.ingested_at)

    finally:
        db.close()

    # --- write to Neo4j ---

    driver = get_driver()
    with driver.session() as neo_session:
        # 1. MERGE AstronomicalObject nodes
        if object_rows:
            neo_session.run(
                """
                UNWIND $rows AS row
                MERGE (o:AstronomicalObject {uuid: row.uuid})
                SET o.ra         = row.ra,
                    o.dec        = row.dec,
                    o.type       = row.type,
                    o.magnitude  = row.magnitude,
                    o.redshift   = row.redshift,
                    o.is_anomaly = row.is_anomaly
                """,
                rows=object_rows,
            )

        # 2. MERGE Observation node
        neo_session.run(
            """
            MERGE (obs:Observation {uuid: $uuid})
            SET obs.telescope   = $telescope,
                obs.ingested_at = $ingested_at
            """,
            uuid=observation_uuid_hex,
            telescope=obs_telescope,
            ingested_at=obs_ingested_at,
        )

        # 3. OBSERVED_IN edges (one UNWIND over all objects)
        if object_rows:
            neo_session.run(
                """
                UNWIND $rows AS row
                MATCH (o:AstronomicalObject {uuid: row.uuid})
                MATCH (obs:Observation      {uuid: $obs_uuid})
                MERGE (o)-[:OBSERVED_IN]->(obs)
                """,
                rows=object_rows,
                obs_uuid=observation_uuid_hex,
            )

        # 4. CatalogEntry nodes + SAME_AS edges
        if catalog_rows:
            neo_session.run(
                """
                UNWIND $rows AS row
                MERGE (c:CatalogEntry {catalog: row.catalog, source_id: row.source_id})
                SET c.name = row.name
                WITH c, row
                MATCH (o:AstronomicalObject {uuid: row.object_uuid})
                MERGE (o)-[:SAME_AS]->(c)
                """,
                rows=catalog_rows,
            )

        # 5. CONTAINS edges
        if contains_pairs:
            neo_session.run(
                """
                UNWIND $pairs AS pair
                MATCH (container:AstronomicalObject {uuid: pair.container_uuid})
                MATCH (contained:AstronomicalObject {uuid: pair.contained_uuid})
                MERGE (container)-[:CONTAINS]->(contained)
                """,
                pairs=contains_pairs,
            )

    logger.info(
        "load_graph: obs=%s nodes=%d catalog_entries=%d contains_edges=%d",
        observation_uuid_hex,
        len(object_rows),
        len(catalog_rows),
        len(contains_pairs),
    )
    return {
        "observation_uuid": observation_uuid_hex,
        "nodes_merged": len(object_rows),
        "catalog_entries_merged": len(catalog_rows),
        "contains_edges": len(contains_pairs),
        "status": "completed",
    }
