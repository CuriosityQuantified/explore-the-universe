"""Classification, cross-match, anomaly, search, and type-filter API endpoints.

GET /api/objects/{object_uuid}/classifications   — full append-only history, newest first
GET /api/objects/{object_uuid}/cross-matches     — all catalog matches, by angular separation
GET /api/observations/{observation_uuid}/anomalies — anomaly-flagged objects (empty list if none)
GET /api/objects/search                          — cone search + type filter (combinable, paginated)
GET /api/objects/types                           — distinct classified_object_type values in DB
"""

import logging
import math
import urllib.parse
from datetime import datetime
from typing import Any, List, Optional, Union

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db.session import get_database_session
from shared.config import settings
from shared.models import (
    AstronomicalObject,
    CatalogCrossMatch,
    ObjectClassification,
)
from shared.s3 import get_s3_client
from pipeline.catalog_clients.simbad_client import resolve_object_name

router = APIRouter(tags=["objects"])


# --- Response Models ---


class ClassificationResponse(BaseModel):
    classification_uuid: str
    predicted_object_type: str
    classification_confidence_score: float
    ml_model_version: str
    feature_extractor_version: str
    feature_vector: Optional[dict[str, Any]]
    is_anomaly_flagged: bool
    anomaly_score: Optional[float]
    anomaly_explanation: Optional[str]
    classified_at: Optional[datetime]


class CrossMatchResponse(BaseModel):
    match_uuid: str
    catalog_name: str
    catalog_source_id: str
    angular_separation_arcseconds: float
    match_probability_score: Optional[float]
    raw_catalog_response: Optional[dict[str, Any]]


class AnomalyResponse(BaseModel):
    object_uuid: str
    sky_coordinate_ra_degrees: float
    sky_coordinate_dec_degrees: float
    classified_object_type: Optional[str]
    predicted_object_type: Optional[str]
    anomaly_score: Optional[float]
    anomaly_explanation: Optional[str]
    catalog_object_name: Optional[str]
    cutout_s3_prefix: Optional[str]


# --- Endpoints ---


@router.get(
    "/api/objects/{object_uuid}/classifications",
    response_model=list[ClassificationResponse],
)
def get_object_classifications(
    object_uuid: str,
    database_session: Session = Depends(get_database_session),
):
    """Return full append-only classification history for an object, newest first."""
    obj = (
        database_session.query(AstronomicalObject)
        .filter(AstronomicalObject.object_uuid == object_uuid)
        .first()
    )
    if obj is None:
        raise HTTPException(
            status_code=404,
            detail=f"Object {object_uuid} not found",
        )

    records = (
        database_session.query(ObjectClassification)
        .filter(ObjectClassification.object_uuid == object_uuid)
        .order_by(ObjectClassification.classified_at.desc())
        .all()
    )

    return [
        ClassificationResponse(
            classification_uuid=str(r.classification_uuid),
            predicted_object_type=r.predicted_object_type,
            classification_confidence_score=r.classification_confidence_score,
            ml_model_version=r.ml_model_version,
            feature_extractor_version=r.feature_extractor_version,
            feature_vector=r.feature_vector,
            is_anomaly_flagged=r.is_anomaly_flagged,
            anomaly_score=r.anomaly_score,
            anomaly_explanation=r.anomaly_explanation,
            classified_at=r.classified_at,
        )
        for r in records
    ]


@router.get(
    "/api/objects/{object_uuid}/cross-matches",
    response_model=list[CrossMatchResponse],
)
def get_object_cross_matches(
    object_uuid: str,
    database_session: Session = Depends(get_database_session),
):
    """Return all catalog cross-match records for an object, ordered by angular separation."""
    obj = (
        database_session.query(AstronomicalObject)
        .filter(AstronomicalObject.object_uuid == object_uuid)
        .first()
    )
    if obj is None:
        raise HTTPException(
            status_code=404,
            detail=f"Object {object_uuid} not found",
        )

    matches = (
        database_session.query(CatalogCrossMatch)
        .filter(CatalogCrossMatch.object_uuid == object_uuid)
        .order_by(CatalogCrossMatch.angular_separation_arcseconds.asc())
        .all()
    )

    return [
        CrossMatchResponse(
            match_uuid=str(m.match_uuid),
            catalog_name=m.catalog_name,
            catalog_source_id=m.catalog_source_id,
            angular_separation_arcseconds=m.angular_separation_arcseconds,
            match_probability_score=m.match_probability_score,
            raw_catalog_response=m.raw_catalog_response,
        )
        for m in matches
    ]


@router.get(
    "/api/observations/{observation_uuid}/anomalies",
    response_model=list[AnomalyResponse],
)
def get_observation_anomalies(
    observation_uuid: str,
    database_session: Session = Depends(get_database_session),
):
    """Return all anomaly-flagged objects for an observation.

    Returns an empty list (not 404) when no anomalies are found.
    """
    flagged_objects = (
        database_session.query(AstronomicalObject)
        .filter(
            AstronomicalObject.source_observation_uuid == observation_uuid,
            AstronomicalObject.is_anomaly_flagged.is_(True),
        )
        .all()
    )

    results = []
    for obj in flagged_objects:
        # Latest classification for anomaly scores/explanations
        latest_clf = (
            database_session.query(ObjectClassification)
            .filter(
                ObjectClassification.object_uuid == obj.object_uuid,
                ObjectClassification.is_anomaly_flagged.is_(True),
            )
            .order_by(ObjectClassification.classified_at.desc())
            .first()
        )

        results.append(
            AnomalyResponse(
                object_uuid=str(obj.object_uuid),
                sky_coordinate_ra_degrees=obj.sky_coordinate_ra_degrees,
                sky_coordinate_dec_degrees=obj.sky_coordinate_dec_degrees,
                classified_object_type=obj.classified_object_type,
                predicted_object_type=(
                    latest_clf.predicted_object_type if latest_clf else None
                ),
                anomaly_score=latest_clf.anomaly_score if latest_clf else None,
                anomaly_explanation=(
                    latest_clf.anomaly_explanation if latest_clf else None
                ),
                catalog_object_name=obj.catalog_object_name,
                cutout_s3_prefix=obj.cutout_s3_prefix,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Cone search + type filter
# ---------------------------------------------------------------------------

# ADR: Coordinate filtering uses a Python-side haversine post-filter on top of a
# SQL bounding-box pre-filter (±dec_margin, ±ra_margin). This avoids requiring the
# PostgreSQL earthdistance or q3c extensions in the deployment environment while
# keeping the DB scan bounded. For datasets >10M objects, migrate to the q3c
# extension (q3c_radial_query) or earthdistance (earth_distance / ll_to_earth) for
# index-accelerated filtering.

def _angular_separation_arcsec(
    ra1: float, dec1: float, ra2: float, dec2: float
) -> float:
    """Haversine angular separation between two sky coordinates, in arcseconds."""
    ra1r, dec1r, ra2r, dec2r = map(math.radians, [ra1, dec1, ra2, dec2])
    dra = ra2r - ra1r
    ddec = dec2r - dec1r
    a = math.sin(ddec / 2) ** 2 + math.cos(dec1r) * math.cos(dec2r) * math.sin(dra / 2) ** 2
    return 2 * math.asin(math.sqrt(min(a, 1.0))) * (180.0 / math.pi) * 3600.0


def _make_cutout_thumbnail_url(cutout_s3_prefix: Optional[str]) -> Optional[str]:
    """Return a 1-hour signed MinIO URL for the cutout PNG, or None if no prefix."""
    if not cutout_s3_prefix:
        return None
    s3 = get_s3_client()
    key = cutout_s3_prefix.rstrip("/") + "/cutout_stretched.png"
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_segmentation, "Key": key},
            ExpiresIn=3600,
        )
    except Exception:
        return None


class ObjectSearchResponse(BaseModel):
    object_uuid: str
    sky_coordinate_ra_degrees: float
    sky_coordinate_dec_degrees: float
    classified_object_type: Optional[str]
    catalog_object_name: Optional[str]
    is_anomaly_flagged: bool
    cutout_thumbnail_url: Optional[str]


class NameSearchResponse(BaseModel):
    results: List[ObjectSearchResponse]
    resolved_ra: Optional[float]
    resolved_dec: Optional[float]
    simbad_name: Optional[str]


@router.get("/api/objects/types", response_model=List[str])
def get_object_types(
    database_session: Session = Depends(get_database_session),
):
    """Return the list of distinct classified_object_type values present in the DB."""
    rows = (
        database_session.query(AstronomicalObject.classified_object_type)
        .filter(AstronomicalObject.classified_object_type.isnot(None))
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


@router.get("/api/objects/search", response_model=Union[NameSearchResponse, List[ObjectSearchResponse]])
def search_objects(
    response: Response,
    ra: Optional[float] = Query(None, description="Right ascension (degrees)"),
    dec: Optional[float] = Query(None, description="Declination (degrees)"),
    radius_arcsec: Optional[float] = Query(None, description="Search radius (arcseconds)"),
    type: Optional[List[str]] = Query(None, description="One or more classified_object_type values"),
    name: Optional[str] = Query(None, max_length=200, description="Object name to resolve via SIMBAD"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    database_session: Session = Depends(get_database_session),
):
    """Cone search, type filter, or SIMBAD name search over AstronomicalObject records.

    Parameters are combinable: supply ra/dec/radius_arcsec for spatial search,
    type for classification filter, or both together.
    Supply name to resolve via SIMBAD then perform a 5-arcsec cone search.
    Returns paginated results with X-Total-Count header. Empty results return [].
    """
    # --- SIMBAD name search mode ---
    if name is not None:
        try:
            resolved = resolve_object_name(name)
        except RuntimeError as exc:
            logger.error("SIMBAD name resolution failed for %r: %s", name, exc)
            return JSONResponse(
                status_code=503,
                content={"detail": "Name resolution service temporarily unavailable. Please try again later."},
            )

        if resolved is None:
            return NameSearchResponse(
                results=[],
                resolved_ra=None,
                resolved_dec=None,
                simbad_name=None,
            )

        resolved_ra, resolved_dec, simbad_name = resolved
        name_radius = 5.0  # arcseconds

        dec_margin = name_radius / 3600.0
        cos_dec = math.cos(math.radians(resolved_dec))
        ra_margin = dec_margin / cos_dec if cos_dec > 1e-9 else 360.0

        query = database_session.query(AstronomicalObject).filter(
            AstronomicalObject.sky_coordinate_dec_degrees.between(
                resolved_dec - dec_margin, resolved_dec + dec_margin
            ),
            AstronomicalObject.sky_coordinate_ra_degrees.between(
                resolved_ra - ra_margin, resolved_ra + ra_margin
            ),
        )
        candidates = query.all()

        with_sep = [
            (obj, _angular_separation_arcsec(resolved_ra, resolved_dec, obj.sky_coordinate_ra_degrees, obj.sky_coordinate_dec_degrees))
            for obj in candidates
        ]
        with_sep = [(obj, sep) for obj, sep in with_sep if sep <= name_radius]
        with_sep.sort(key=lambda x: x[1])

        total = len(with_sep)
        page = with_sep[offset: offset + limit]
        objs = [obj for obj, _ in page]

        response.headers["X-Total-Count"] = str(total)

        results = [
            ObjectSearchResponse(
                object_uuid=str(obj.object_uuid),
                sky_coordinate_ra_degrees=obj.sky_coordinate_ra_degrees,
                sky_coordinate_dec_degrees=obj.sky_coordinate_dec_degrees,
                classified_object_type=obj.classified_object_type,
                catalog_object_name=obj.catalog_object_name,
                is_anomaly_flagged=obj.is_anomaly_flagged,
                cutout_thumbnail_url=_make_cutout_thumbnail_url(obj.cutout_s3_prefix),
            )
            for obj in objs
        ]

        return NameSearchResponse(
            results=results,
            resolved_ra=resolved_ra,
            resolved_dec=resolved_dec,
            simbad_name=simbad_name,
        )

    # --- Cone / type search mode ---
    is_cone = ra is not None and dec is not None and radius_arcsec is not None

    if is_cone:
        # Bounding-box pre-filter keeps the DB scan bounded (see ADR comment above).
        dec_margin = radius_arcsec / 3600.0
        cos_dec = math.cos(math.radians(dec))
        ra_margin = dec_margin / cos_dec if cos_dec > 1e-9 else 360.0

        query = database_session.query(AstronomicalObject).filter(
            AstronomicalObject.sky_coordinate_dec_degrees.between(
                dec - dec_margin, dec + dec_margin
            ),
            AstronomicalObject.sky_coordinate_ra_degrees.between(
                ra - ra_margin, ra + ra_margin
            ),
        )
        if type:
            query = query.filter(AstronomicalObject.classified_object_type.in_(type))

        candidates = query.all()

        # Exact haversine filter + sort by angular separation
        with_sep = [
            (obj, _angular_separation_arcsec(ra, dec, obj.sky_coordinate_ra_degrees, obj.sky_coordinate_dec_degrees))
            for obj in candidates
        ]
        with_sep = [(obj, sep) for obj, sep in with_sep if sep <= radius_arcsec]
        with_sep.sort(key=lambda x: x[1])

        total = len(with_sep)
        page = with_sep[offset: offset + limit]
        objs = [obj for obj, _ in page]
    else:
        query = database_session.query(AstronomicalObject)
        if type:
            query = query.filter(AstronomicalObject.classified_object_type.in_(type))

        total = query.count()
        objs = query.all()[offset: offset + limit]

    response.headers["X-Total-Count"] = str(total)

    return [
        ObjectSearchResponse(
            object_uuid=str(obj.object_uuid),
            sky_coordinate_ra_degrees=obj.sky_coordinate_ra_degrees,
            sky_coordinate_dec_degrees=obj.sky_coordinate_dec_degrees,
            classified_object_type=obj.classified_object_type,
            catalog_object_name=obj.catalog_object_name,
            is_anomaly_flagged=obj.is_anomaly_flagged,
            cutout_thumbnail_url=_make_cutout_thumbnail_url(obj.cutout_s3_prefix),
        )
        for obj in objs
    ]


# ---------------------------------------------------------------------------
# Object detail
# ---------------------------------------------------------------------------

_CATALOG_URL_TEMPLATES: dict[str, str] = {
    "SIMBAD": "https://simbad.u-strasbg.fr/simbad/sim-id?Ident={}",
    "NED": "https://ned.ipac.caltech.edu/byname?objname={}",
    "Gaia": "https://gea.esac.esa.int/archive/#search;table=gaiadr3.gaia_source;qstring=source_id={}",
    "2MASS": "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?catalog=fp_psc&constraints=designation+like+%27{}%27",
    "SDSS": "https://skyserver.sdss.org/dr18/SearchTools/IQS?name={}",
}


def _catalog_external_url(catalog_name: str, source_id: str) -> Optional[str]:
    tmpl = _CATALOG_URL_TEMPLATES.get(catalog_name)
    if tmpl is None:
        return None
    return tmpl.format(urllib.parse.quote(str(source_id), safe=""))


class CrossMatchDetailResponse(BaseModel):
    match_uuid: str
    catalog_name: str
    catalog_source_id: str
    angular_separation_arcseconds: float
    match_probability_score: Optional[float]
    external_url: Optional[str]


class ClassificationDetailResponse(BaseModel):
    classification_uuid: str
    predicted_object_type: str
    classification_confidence_score: float
    ml_model_version: str
    classified_at: Optional[datetime]
    is_anomaly_flagged: bool
    anomaly_score: Optional[float]
    anomaly_explanation: Optional[str]


class ObjectDetailResponse(BaseModel):
    object_uuid: str
    source_observation_uuid: str
    sky_coordinate_ra_degrees: float
    sky_coordinate_dec_degrees: float
    bounding_box_pixels: Optional[dict[str, Any]]
    classified_object_type: Optional[str]
    catalog_object_name: Optional[str]
    catalog_magnitude: Optional[float]
    catalog_redshift: Optional[float]
    is_anomaly_flagged: bool
    physical_properties: Optional[dict[str, Any]]
    segmentation_mask_rle: Optional[dict[str, Any]]
    cutout_url: Optional[str]
    cross_matches: list[CrossMatchDetailResponse]
    latest_classification: Optional[ClassificationDetailResponse]


@router.get("/api/objects/{object_uuid}", response_model=ObjectDetailResponse)
def get_object_detail(
    object_uuid: str,
    database_session: Session = Depends(get_database_session),
):
    """Return the full record for a single astronomical object.

    Includes a signed cutout URL, segmentation mask RLE, all catalog cross-matches
    ordered by angular separation with external catalog links, and the latest ML
    classification. Returns 404 for unknown UUIDs.
    """
    obj = (
        database_session.query(AstronomicalObject)
        .filter(AstronomicalObject.object_uuid == object_uuid)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail=f"Object {object_uuid} not found")

    matches = (
        database_session.query(CatalogCrossMatch)
        .filter(CatalogCrossMatch.object_uuid == object_uuid)
        .order_by(CatalogCrossMatch.angular_separation_arcseconds.asc())
        .all()
    )

    latest_clf = (
        database_session.query(ObjectClassification)
        .filter(ObjectClassification.object_uuid == object_uuid)
        .order_by(ObjectClassification.classified_at.desc())
        .first()
    )

    return ObjectDetailResponse(
        object_uuid=str(obj.object_uuid),
        source_observation_uuid=str(obj.source_observation_uuid),
        sky_coordinate_ra_degrees=obj.sky_coordinate_ra_degrees,
        sky_coordinate_dec_degrees=obj.sky_coordinate_dec_degrees,
        bounding_box_pixels=obj.bounding_box_pixels,
        classified_object_type=obj.classified_object_type,
        catalog_object_name=obj.catalog_object_name,
        catalog_magnitude=obj.catalog_magnitude,
        catalog_redshift=obj.catalog_redshift,
        is_anomaly_flagged=obj.is_anomaly_flagged,
        physical_properties=obj.physical_properties,
        segmentation_mask_rle=obj.segmentation_mask_rle,
        cutout_url=_make_cutout_thumbnail_url(obj.cutout_s3_prefix),
        cross_matches=[
            CrossMatchDetailResponse(
                match_uuid=str(m.match_uuid),
                catalog_name=m.catalog_name,
                catalog_source_id=m.catalog_source_id,
                angular_separation_arcseconds=m.angular_separation_arcseconds,
                match_probability_score=m.match_probability_score,
                external_url=_catalog_external_url(m.catalog_name, m.catalog_source_id),
            )
            for m in matches
        ],
        latest_classification=(
            ClassificationDetailResponse(
                classification_uuid=str(latest_clf.classification_uuid),
                predicted_object_type=latest_clf.predicted_object_type,
                classification_confidence_score=latest_clf.classification_confidence_score,
                ml_model_version=latest_clf.ml_model_version,
                classified_at=latest_clf.classified_at,
                is_anomaly_flagged=latest_clf.is_anomaly_flagged,
                anomaly_score=latest_clf.anomaly_score,
                anomaly_explanation=latest_clf.anomaly_explanation,
            )
            if latest_clf
            else None
        ),
    )
