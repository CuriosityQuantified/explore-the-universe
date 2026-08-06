"""Stub Celery task: cross-match astronomical objects against external catalogs.

Implementation deferred to Phase 5 Plan 2.
"""

from pipeline.celery_app import celery_app


@celery_app.task(bind=True, acks_late=True)
def cross_match_catalogs(self, cutout_result: dict) -> dict:
    """Cross-match detected objects against SIMBAD, NED, SDSS, and Gaia.

    Seventh step in the 9-task pipeline chain.
    Receives the output dict from generate_cutouts.
    """
    raise NotImplementedError(
        "cross_match_catalogs implementation is deferred to Plan 05-02"
    )
