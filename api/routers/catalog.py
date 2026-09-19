"""Paginated object browsing and live catalog coverage."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import BigInteger, and_, case, cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from api.db.session import get_database_session
from pipeline.catalog import normalize_name
from shared.models import AstronomicalObject as Object

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


class CatalogEntry(BaseModel):
    object_uuid: UUID
    catalog_object_name: str | None
    classified_object_type: str | None
    catalog_magnitude: float | None
    catalog_redshift: float | None
    sky_coordinate_ra_degrees: float
    sky_coordinate_dec_degrees: float
    has_image: bool
    constellation: str | None


class CatalogPage(BaseModel):
    results: list[CatalogEntry]
    total_count: int
    limit: int
    offset: int


@router.get("/objects", response_model=CatalogPage)
def browse_objects(
    session: Session = Depends(get_database_session),
    q: str = Query("", max_length=120),
    type: str | None = Query(None, max_length=80),
    has_image: bool | None = None,
    hemisphere: Literal["north", "south"] | None = None,
    magnitude_min: float | None = Query(None, allow_inf_nan=False),
    magnitude_max: float | None = Query(None, allow_inf_nan=False),
    sort_by: Literal["name", "type", "magnitude", "redshift", "ra", "dec"] = "name",
    sort_order: Literal["asc", "desc"] = "asc",
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Browse all indexed objects locally, with filtering and stable SQL pagination."""
    if magnitude_min is not None and magnitude_max is not None and magnitude_min > magnitude_max:
        raise HTTPException(422, "Minimum magnitude must not exceed maximum magnitude")

    image_available = and_(Object.cutout_s3_prefix.isnot(None), Object.cutout_s3_prefix != "")
    conditions = []
    if query := q.strip():
        # Treat SQL wildcard characters as literal user input. Normalized aliases
        # also match forms such as 'NGC 0224' and partial common names.
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        names = Object.catalog_object_name.ilike(f"%{escaped}%", escape="\\")
        if normalized := normalize_name(query):
            alias_values = case(
                (func.jsonb_typeof(Object.physical_properties["aliases"]) == "array",
                 Object.physical_properties["aliases"]),
                else_=cast(literal("[]"), JSONB),
            )
            aliases = func.jsonb_array_elements_text(alias_values).table_valued("value").alias("catalog_alias")
            alias_match = select(1).select_from(aliases).where(
                aliases.c.value.contains(normalized, autoescape=True)
            ).correlate(Object).exists()
            names = or_(names, alias_match)
        conditions.append(names)
    if type:
        conditions.append(Object.classified_object_type == type)
    if has_image is not None:
        conditions.append(image_available == has_image)
    if hemisphere == "north":
        conditions.append(Object.sky_coordinate_dec_degrees >= 0)
    elif hemisphere == "south":
        conditions.append(Object.sky_coordinate_dec_degrees < 0)
    if magnitude_min is not None:
        conditions.append(Object.catalog_magnitude >= magnitude_min)
    if magnitude_max is not None:
        conditions.append(Object.catalog_magnitude <= magnitude_max)

    columns = {
        "name": func.lower(Object.catalog_object_name),
        "type": Object.classified_object_type,
        "magnitude": Object.catalog_magnitude,
        "redshift": Object.catalog_redshift,
        "ra": Object.sky_coordinate_ra_degrees,
        "dec": Object.sky_coordinate_dec_degrees,
    }
    column = columns[sort_by]
    order = (column.desc() if sort_order == "desc" else column.asc()).nulls_last()
    total = session.scalar(select(func.count()).select_from(Object).where(*conditions))
    rows = session.execute(select(
        Object.object_uuid, Object.catalog_object_name, Object.classified_object_type,
        Object.catalog_magnitude, Object.catalog_redshift,
        Object.sky_coordinate_ra_degrees, Object.sky_coordinate_dec_degrees,
        image_available.label("has_image"),
        Object.physical_properties["constellation"].astext.label("constellation"),
    ).where(*conditions).order_by(
        order, func.lower(Object.catalog_object_name).asc().nulls_last(), Object.object_uuid.asc(),
    ).limit(limit).offset(offset)).mappings().all()
    return CatalogPage(results=[CatalogEntry(**row) for row in rows], total_count=total,
                       limit=limit, offset=offset)


@router.get("/summary")
def catalog_summary(session: Session = Depends(get_database_session)):
    row = session.execute(select(
        func.count(Object.object_uuid),
        func.count(Object.cutout_s3_prefix),
        func.count(Object.object_uuid).filter(Object.sky_coordinate_dec_degrees >= 0),
        func.count(Object.object_uuid).filter(Object.sky_coordinate_dec_degrees < 0),
        func.coalesce(func.sum(Object.physical_properties["imagery_bytes"].astext.cast(BigInteger)), 0),
    ).where(Object.classification_source_catalog == "OpenNGC")).one()
    return dict(objects=row[0], images_ready=row[1], images_queued=row[0] - row[1],
                northern_objects=row[2], southern_objects=row[3], stored_bytes=row[4])
