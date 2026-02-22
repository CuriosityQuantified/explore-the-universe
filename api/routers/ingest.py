"""Ingest API endpoints for triggering and monitoring the pipeline.

POST /api/ingest - Trigger ingestion of a JWST observation
GET /api/ingest/{observation_uuid}/status - Check pipeline progress
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.db.session import get_database_session
from pipeline.tasks.ingest import ingest_observation
from shared.models import Observation, ProcessingStep

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


# --- Request/Response Models ---


class IngestRequest(BaseModel):
    """Request body for POST /api/ingest."""

    archive_observation_id: str = Field(
        ...,
        description="JWST observation ID (e.g., 'jw02731001001_04101_00001_nrca1')",
    )
    archive_program_id: str | None = Field(
        default=None,
        description="Optional JWST program ID (e.g., '2731')",
    )


class IngestResponse(BaseModel):
    """Response body for POST /api/ingest (202 Accepted)."""

    observation_uuid: str
    status: str = "pipeline_started"
    message: str = (
        "Ingestion pipeline started. "
        "Use GET /api/ingest/{observation_uuid}/status to check progress."
    )


class IngestStatusResponse(BaseModel):
    """Response body for GET /api/ingest/{observation_uuid}/status."""

    observation_uuid: str
    archive_observation_id: str
    pipeline_status: str
    steps: list[dict]
    provenance: dict | None = None


# --- Endpoints ---


@router.post("", status_code=202, response_model=IngestResponse)
def trigger_ingest(
    request: IngestRequest,
    database_session: Session = Depends(get_database_session),
):
    """Trigger the ingestion pipeline for a JWST observation.

    Creates an Observation record and dispatches the Celery chain:
    download_fits -> validate_wcs -> generate_tiles.

    Returns 202 Accepted immediately -- the pipeline runs asynchronously.
    """
    result = ingest_observation.delay(
        request.archive_observation_id,
        request.archive_program_id,
    )

    # The Celery task returns a dict, but .delay() gives us an AsyncResult.
    # We need the observation_uuid from the task, but the task hasn't
    # completed yet. Instead, we wait briefly for the initial task to
    # create the Observation and return its UUID.
    #
    # However, since ingest_observation creates the DB record synchronously
    # before dispatching the chain, we can look it up by archive_observation_id.
    observation = (
        database_session.query(Observation)
        .filter(
            Observation.archive_observation_id
            == request.archive_observation_id
        )
        .order_by(Observation.ingested_at.desc())
        .first()
    )

    if observation is not None:
        observation_uuid = str(observation.observation_uuid)
    else:
        # Fallback: return the Celery task ID if observation not yet created
        observation_uuid = result.id

    return IngestResponse(
        observation_uuid=observation_uuid,
        status="pipeline_started",
        message=(
            "Ingestion pipeline started. "
            f"Use GET /api/ingest/{observation_uuid}/status to check progress."
        ),
    )


@router.get(
    "/{observation_uuid}/status",
    response_model=IngestStatusResponse,
)
def get_ingest_status(
    observation_uuid: str,
    database_session: Session = Depends(get_database_session),
):
    """Check the status of an ingestion pipeline.

    Returns the observation details including all processing steps
    and provenance metadata.
    """
    observation = (
        database_session.query(Observation)
        .filter(Observation.observation_uuid == observation_uuid)
        .first()
    )

    if observation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Observation {observation_uuid} not found",
        )

    # Query processing steps ordered by start time
    steps = (
        database_session.query(ProcessingStep)
        .filter(ProcessingStep.observation_uuid == observation.observation_uuid)
        .order_by(ProcessingStep.step_started_at.asc())
        .all()
    )

    steps_data = [
        {
            "step_name": step.step_name,
            "step_status": step.step_status.value if step.step_status else None,
            "step_started_at": (
                step.step_started_at.isoformat() if step.step_started_at else None
            ),
            "step_completed_at": (
                step.step_completed_at.isoformat()
                if step.step_completed_at
                else None
            ),
            "error_message_text": step.error_message_text,
        }
        for step in steps
    ]

    provenance = {
        "telescope_name": observation.telescope_name,
        "instrument_name": observation.instrument_name,
        "spectral_filters": observation.spectral_filters,
        "total_exposure_seconds": observation.total_exposure_seconds,
        "pointing_ra_degrees": observation.pointing_ra_degrees,
        "pointing_dec_degrees": observation.pointing_dec_degrees,
    }

    return IngestStatusResponse(
        observation_uuid=str(observation.observation_uuid),
        archive_observation_id=observation.archive_observation_id,
        pipeline_status=observation.pipeline_status.value,
        steps=steps_data,
        provenance=provenance,
    )
