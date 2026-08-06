"""Stub Celery task: classify astronomical objects using ML.

Implementation deferred to Phase 5 Plan 2.
"""

from pipeline.celery_app import celery_app


@celery_app.task(bind=True, acks_late=True)
def classify_objects(self, cross_match_result: dict) -> dict:
    """Extract morphological features and classify objects using a trained ML model.

    Eighth step in the 9-task pipeline chain.
    Receives the output dict from cross_match_catalogs.
    """
    raise NotImplementedError(
        "classify_objects implementation is deferred to Plan 05-02"
    )
