"""Observations list API endpoint.

GET /api/observations — all ingested observations with pipeline status,
counts of detected/classified/anomaly objects, and processing step timeline.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db.session import get_database_session
from shared.models import AstronomicalObject, Observation, ProcessingStep

router = APIRouter(prefix="/api/observations", tags=["observations"])


class ProcessingStepSummary(BaseModel):
    step_name: str
    step_status: Optional[str]
    step_started_at: Optional[str]
    step_completed_at: Optional[str]


class ObservationSummaryResponse(BaseModel):
    observation_uuid: str
    archive_observation_id: str
    pipeline_status: str
    ingested_at: str
    object_count: int
    classified_count: int
    anomaly_count: int
    steps: list[ProcessingStepSummary]


@router.get("", response_model=list[ObservationSummaryResponse])
def list_observations(
    database_session: Session = Depends(get_database_session),
) -> list[ObservationSummaryResponse]:
    """Return all ingested observations with pipeline status and object counts."""
    observations = (
        database_session.query(Observation)
        .order_by(Observation.ingested_at.desc())
        .all()
    )

    result = []
    for obs in observations:
        obs_uuid = obs.observation_uuid

        object_count = (
            database_session.query(AstronomicalObject)
            .filter(AstronomicalObject.source_observation_uuid == obs_uuid)
            .count()
        )
        classified_count = (
            database_session.query(AstronomicalObject)
            .filter(
                AstronomicalObject.source_observation_uuid == obs_uuid,
                AstronomicalObject.classified_object_type.isnot(None),
            )
            .count()
        )
        anomaly_count = (
            database_session.query(AstronomicalObject)
            .filter(
                AstronomicalObject.source_observation_uuid == obs_uuid,
                AstronomicalObject.is_anomaly_flagged == True,  # noqa: E712
            )
            .count()
        )

        steps = (
            database_session.query(ProcessingStep)
            .filter(ProcessingStep.observation_uuid == obs_uuid)
            .order_by(ProcessingStep.step_started_at.asc())
            .all()
        )

        result.append(
            ObservationSummaryResponse(
                observation_uuid=str(obs_uuid),
                archive_observation_id=obs.archive_observation_id,
                pipeline_status=obs.pipeline_status.value,
                ingested_at=(
                    obs.ingested_at.isoformat() if obs.ingested_at else ""
                ),
                object_count=object_count,
                classified_count=classified_count,
                anomaly_count=anomaly_count,
                steps=[
                    ProcessingStepSummary(
                        step_name=s.step_name,
                        step_status=(
                            s.step_status.value if s.step_status else None
                        ),
                        step_started_at=(
                            s.step_started_at.isoformat()
                            if s.step_started_at
                            else None
                        ),
                        step_completed_at=(
                            s.step_completed_at.isoformat()
                            if s.step_completed_at
                            else None
                        ),
                    )
                    for s in steps
                ],
            )
        )

    return result
