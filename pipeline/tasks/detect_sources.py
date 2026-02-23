"""SEP source detection Celery task (stub -- implemented in Plan 04-02)."""

from pipeline.celery_app import celery_app


@celery_app.task(bind=True, acks_late=True)
def detect_sources(self, tile_result: dict) -> dict:
    raise NotImplementedError(
        "detect_sources task not yet implemented -- see Plan 04-02"
    )
