"""Classification, cross-match, and anomaly API endpoints.

GET /api/objects/{object_uuid}/classifications   — full append-only history, newest first
GET /api/objects/{object_uuid}/cross-matches     — all catalog matches, by angular separation
GET /api/observations/{observation_uuid}/anomalies — anomaly-flagged objects (empty list if none)
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db.session import get_database_session
from shared.models import (
    AstronomicalObject,
    CatalogCrossMatch,
    ObjectClassification,
)

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
