"""Pipeline orchestrator Celery task for JWST observations.

Creates an Observation record in PostgreSQL, then chains the full pipeline:
download_fits -> validate_wcs -> generate_tiles. This is the entry point
triggered by the ingest API endpoint.

Usage:
    ingest_observation.delay(archive_observation_id, archive_program_id)
"""

import logging
import uuid

from celery import chain
from sqlalchemy import func as sql_func

from api.db.session import SessionLocal
from pipeline.celery_app import celery_app
from pipeline.tasks.download import download_fits
from pipeline.tasks.tile import generate_tiles
from pipeline.tasks.validate_wcs import validate_wcs
from shared.models import Observation, PipelineStatus

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    acks_late=True,
)
def ingest_observation(
    self,
    archive_observation_id: str,
    archive_program_id: str | None = None,
) -> dict:
    """Create an Observation record and kick off the full pipeline chain.

    Creates the Observation in PostgreSQL with status 'downloading', then
    builds and dispatches a Celery chain: download_fits -> validate_wcs ->
    generate_tiles. Returns immediately with the observation UUID and
    Celery task ID for status polling.

    Args:
        archive_observation_id: MAST observation ID
            (e.g., 'jw02731001001_04101_00001_nrca1').
        archive_program_id: Optional JWST program ID (e.g., '2731').

    Returns:
        Dict with observation_uuid, celery_task_id, and status.
    """
    database_session = SessionLocal()

    try:
        # --- Step a: Create Observation record ---
        observation = Observation(
            observation_uuid=uuid.uuid4(),
            archive_observation_id=archive_observation_id,
            archive_program_id=archive_program_id,
            telescope_name="JWST",
            instrument_name="UNKNOWN",
            pipeline_status=PipelineStatus.downloading,
        )
        database_session.add(observation)
        database_session.commit()
        database_session.refresh(observation)

        observation_uuid = observation.observation_uuid
        observation_uuid_hex = str(observation_uuid)

        logger.info(
            "Created Observation %s for archive_observation_id=%s, program=%s",
            observation_uuid_hex,
            archive_observation_id,
            archive_program_id,
        )

        # --- Step b: Build and dispatch Celery chain ---
        pipeline = chain(
            download_fits.s(
                observation_uuid_hex,
                archive_observation_id,
                archive_program_id,
            ),
            validate_wcs.s(),
            generate_tiles.s(),
        )
        result = pipeline.apply_async()

        logger.info(
            "Pipeline chain dispatched for observation %s: celery_task_id=%s",
            observation_uuid_hex,
            result.id,
        )

        # --- Step c: Return result ---
        return {
            "observation_uuid": observation_uuid_hex,
            "celery_task_id": result.id,
            "status": "pipeline_started",
        }

    except Exception as exception:
        logger.exception(
            "Failed to create observation or dispatch pipeline for "
            "archive_observation_id=%s: %s",
            archive_observation_id,
            exception,
        )
        database_session.rollback()
        raise

    finally:
        database_session.close()
