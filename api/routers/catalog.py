"""Live catalog coverage, including records whose survey imagery is queued."""
from fastapi import APIRouter, Depends
from sqlalchemy import BigInteger, func, select
from sqlalchemy.orm import Session
from api.db.session import get_database_session
from shared.models import AstronomicalObject as Object

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


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
