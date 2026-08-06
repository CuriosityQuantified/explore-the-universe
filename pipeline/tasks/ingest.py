"""Pipeline orchestrator Celery task for JWST observations.

Dispatches the full 9-task pipeline chain:
  download_fits -> validate_wcs -> generate_tiles -> detect_sources ->
  segment_sam -> generate_cutouts -> cross_match_catalogs ->
  classify_objects -> detect_anomalies.

The Observation record is created by the API endpoint before this task
is dispatched.  PipelineStatus.completed is set by detect_anomalies
(the final task), not by generate_cutouts.

Usage:
    ingest_observation.delay(observation_uuid_hex, archive_observation_id, archive_program_id)
"""

import logging

from celery import chain

from pipeline.celery_app import celery_app
from pipeline.tasks.classify_objects import classify_objects
from pipeline.tasks.cross_match_catalogs import cross_match_catalogs
from pipeline.tasks.detect_anomalies import detect_anomalies
from pipeline.tasks.detect_sources import detect_sources
from pipeline.tasks.download import download_fits
from pipeline.tasks.generate_cutouts import generate_cutouts
from pipeline.tasks.segment_sam import segment_sam
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
    """Dispatch the full 9-task pipeline chain for a pre-created Observation.

    The Observation record must already exist in PostgreSQL (created by
    the API endpoint). This task builds and dispatches the Celery chain:
    download_fits -> validate_wcs -> generate_tiles -> detect_sources ->
    segment_sam -> generate_cutouts -> cross_match_catalogs ->
    classify_objects -> detect_anomalies.

    PipelineStatus.completed is set by detect_anomalies (the final task).

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
        detect_sources.s(),
        segment_sam.s(),
        generate_cutouts.s(),
        cross_match_catalogs.s(),
        classify_objects.s(),
        detect_anomalies.s(),
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
