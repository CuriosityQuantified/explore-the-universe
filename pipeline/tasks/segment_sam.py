"""SAM segmentation Celery task (stub -- implemented in Plan 04-02)."""

from pipeline.celery_app import celery_app


@celery_app.task(bind=True, acks_late=True)
def segment_sam(self, detection_result: dict) -> dict:
    raise NotImplementedError(
        "segment_sam task not yet implemented -- see Plan 04-02"
    )
