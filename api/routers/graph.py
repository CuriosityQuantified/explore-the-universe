"""Graph property query and neighborhood API.

GET /api/graph/query                    — filter AstronomicalObject nodes by properties
GET /api/objects/{uuid}/graph-neighbors — 1-hop neighborhood for a UUID
"""
import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from neo4j import Session
from pydantic import BaseModel

from api.db.neo4j import get_neo4j_session
from shared.config import settings
from shared.s3 import get_s3_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["graph"])

# ---------------------------------------------------------------------------
# Cypher queries
# ---------------------------------------------------------------------------

_QUERY_CYPHER = """
MATCH (o:AstronomicalObject)
WHERE ($type IS NULL OR o.type = $type)
  AND ($magnitude_min IS NULL OR o.magnitude >= $magnitude_min)
  AND ($magnitude_max IS NULL OR o.magnitude <= $magnitude_max)
  AND ($redshift_min IS NULL OR o.redshift >= $redshift_min)
  AND ($redshift_max IS NULL OR o.redshift <= $redshift_max)
  AND ($is_anomaly IS NULL OR o.is_anomaly = $is_anomaly)
RETURN o.uuid AS uuid, o.type AS type, o.magnitude AS magnitude,
       o.redshift AS redshift, o.ra AS ra, o.dec AS dec
ORDER BY o.magnitude ASC
SKIP $skip LIMIT $limit
"""

_NEIGHBORS_CYPHER = """
MATCH (o:AstronomicalObject {uuid: $uuid})
OPTIONAL MATCH (o)-[:CONTAINS]->(child:AstronomicalObject)
OPTIONAL MATCH (parent:AstronomicalObject)-[:CONTAINS]->(o)
OPTIONAL MATCH (o)-[:SAME_AS]->(cat:CatalogEntry)
RETURN
  collect(DISTINCT {uuid: child.uuid, type: child.type, cutout_s3_prefix: child.cutout_s3_prefix})[..10] AS contains_children,
  collect(DISTINCT {uuid: parent.uuid, type: parent.type, cutout_s3_prefix: parent.cutout_s3_prefix})[..10] AS contained_by,
  collect(DISTINCT {catalog: cat.catalog, source_id: cat.source_id}) AS catalog_entries
"""

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class GraphQueryResult(BaseModel):
    uuid: str
    type: Optional[str] = None
    magnitude: Optional[float] = None
    redshift: Optional[float] = None
    ra: Optional[float] = None
    dec: Optional[float] = None


class GraphQueryResponse(BaseModel):
    results: List[GraphQueryResult]
    limit: int
    offset: int


class GraphNeighborNode(BaseModel):
    uuid: str
    type: Optional[str] = None
    thumbnail_url: Optional[str] = None


class GraphCatalogEntry(BaseModel):
    catalog: str
    source_id: str


class GraphNeighborsResponse(BaseModel):
    in_graph: bool
    contains_children: List[GraphNeighborNode] = []
    contained_by: List[GraphNeighborNode] = []
    catalog_entries: List[GraphCatalogEntry] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_S3_PREFIX_RE = re.compile(r"^[a-zA-Z0-9/_\-]{1,512}$")


def _thumbnail_url(cutout_s3_prefix: Optional[str]) -> Optional[str]:
    """Return a 1-hour presigned MinIO URL for the cutout thumbnail, or None."""
    if not cutout_s3_prefix:
        return None
    if not _S3_PREFIX_RE.match(cutout_s3_prefix):
        logger.warning("Rejecting suspicious cutout_s3_prefix from graph: %r", cutout_s3_prefix)
        return None
    key = cutout_s3_prefix.rstrip("/") + "/cutout_stretched.png"
    try:
        return get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_segmentation, "Key": key},
            ExpiresIn=3600,
        )
    except Exception:
        logger.warning("Could not generate presigned URL for prefix %s", cutout_s3_prefix)
        return None


def _build_neighbors(raw: List[dict]) -> List[GraphNeighborNode]:
    """Convert a raw Neo4j neighbor list to GraphNeighborNode, dropping null-uuid entries."""
    return [
        GraphNeighborNode(
            uuid=n["uuid"],
            type=n.get("type"),
            thumbnail_url=_thumbnail_url(n.get("cutout_s3_prefix")),
        )
        for n in (raw or [])
        if n.get("uuid") is not None
    ]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/api/graph/query", response_model=GraphQueryResponse)
def query_graph(
    type: Optional[str] = Query(None, max_length=100),
    magnitude_min: Optional[float] = Query(None),
    magnitude_max: Optional[float] = Query(None),
    redshift_min: Optional[float] = Query(None),
    redshift_max: Optional[float] = Query(None),
    is_anomaly: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    neo4j_session: Session = Depends(get_neo4j_session),
) -> GraphQueryResponse:
    """Query AstronomicalObject nodes in Neo4j by property filters.

    All filter parameters are optional and combinable.  Results are ordered
    by magnitude ascending and paginated via limit/offset.
    """
    try:
        result = neo4j_session.run(
            _QUERY_CYPHER,
            type=type,
            magnitude_min=magnitude_min,
            magnitude_max=magnitude_max,
            redshift_min=redshift_min,
            redshift_max=redshift_max,
            is_anomaly=is_anomaly,
            skip=offset,
            limit=limit,
        )
        rows = result.data()
    except Exception:
        logger.exception("Neo4j query failed in /api/graph/query")
        raise HTTPException(status_code=503, detail="Graph database unavailable")
    return GraphQueryResponse(
        results=[GraphQueryResult(**row) for row in rows],
        limit=limit,
        offset=offset,
    )


@router.get("/api/objects/{uuid}/graph-neighbors", response_model=GraphNeighborsResponse)
def get_graph_neighbors(
    uuid: str = Path(..., max_length=36),
    neo4j_session: Session = Depends(get_neo4j_session),
) -> GraphNeighborsResponse:
    """Return 1-hop neighbors for an AstronomicalObject in the knowledge graph.

    Returns CONTAINS children (objects this one contains), CONTAINS parents
    (objects that contain this one), and SAME_AS catalog entries.

    If no Neo4j node exists for the UUID, returns ``{"in_graph": false}``.
    """
    try:
        result = neo4j_session.run(_NEIGHBORS_CYPHER, uuid=uuid)
        rows = result.data()
    except Exception:
        logger.exception("Neo4j query failed in /api/objects/%s/graph-neighbors", uuid)
        raise HTTPException(status_code=503, detail="Graph database unavailable")
    if not rows:
        return GraphNeighborsResponse(in_graph=False)

    row = rows[0]

    # Filter out null entries that arise when OPTIONAL MATCH finds nothing.
    catalog_entries = [
        GraphCatalogEntry(**c)
        for c in (row.get("catalog_entries") or [])
        if c.get("catalog") is not None and c.get("source_id") is not None
    ]

    return GraphNeighborsResponse(
        in_graph=True,
        contains_children=_build_neighbors(row.get("contains_children") or []),
        contained_by=_build_neighbors(row.get("contained_by") or []),
        catalog_entries=catalog_entries,
    )
