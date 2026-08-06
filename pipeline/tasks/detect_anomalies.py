"""Stub Celery task: score anomalies and flag novel objects.

This is the final task in the 9-step pipeline chain.  It owns
PipelineStatus.completed — generate_cutouts no longer sets it.

Implementation deferred to Phase 5 Plan 3.
"""

from pipeline.celery_app import celery_app


@celery_app.task(bind=True, acks_late=True)
def detect_anomalies(self, classification_result: dict) -> dict:
    """Score objects for anomalies and flag novel detections.

    Ninth (final) step in the 9-task pipeline chain.
    Receives the output dict from classify_objects.
    Sets PipelineStatus.completed on the observation upon success.
    """
    raise NotImplementedError(
        "detect_anomalies implementation is deferred to Plan 05-03"
    )
