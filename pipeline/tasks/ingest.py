"""Pipeline orchestrator Celery task for JWST observations.

Dispatches the full pipeline chain: download_fits -> validate_wcs ->
generate_tiles. The Observation record is created by the API endpoint
before this task is dispatched.

Usage:
    ingest_observation.delay(observation_uuid_hex, archive_observation_id, archive_program_id)
"""

import logging

from celery import chain

from pipeline.celery_app import celery_app
from pipeline.tasks.download import download_fits
from pipeline.tasks.tile import generate_tiles
from pipeline.tasks.validate_wcs import validate_wcs

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    acks_late=True,
)
def ingest_observation(
    self,
    observation_uuid_hex: str,
    archive_observation_id: str,
    archive_program_id: str | None = None,
) -> dict:
    """Dispatch the full pipeline chain for a pre-created Observation.

    The Observation record must already exist in PostgreSQL (created by
    the API endpoint). This task builds and dispatches the Celery chain:
    download_fits -> validate_wcs -> generate_tiles.

    Args:
        observation_uuid_hex: UUID of the pre-created Observation record.
        archive_observation_id: MAST observation ID
            (e.g., 'jw02731001001_04101_00001_nrca1').
        archive_program_id: Optional JWST program ID (e.g., '2731').

    Returns:
        Dict with observation_uuid, celery_task_id, and status.
    """
    logger.info(
        "Dispatching pipeline chain for observation %s "
        "(archive_observation_id=%s, program=%s)",
        observation_uuid_hex,
        archive_observation_id,
        archive_program_id,
    )

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

    return {
        "observation_uuid": observation_uuid_hex,
        "celery_task_id": result.id,
        "status": "pipeline_started",
    }
