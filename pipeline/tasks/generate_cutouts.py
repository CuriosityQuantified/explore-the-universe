"""Cutout generation Celery task (stub -- implemented in Plan 04-03)."""

from pipeline.celery_app import celery_app


@celery_app.task(bind=True, acks_late=True)
def generate_cutouts(self, segmentation_result: dict) -> dict:
    raise NotImplementedError(
        "generate_cutouts task not yet implemented -- see Plan 04-03"
    )
