from pipeline.celery_app import celery_app


@celery_app.task
def test_pipeline_task(observation_uuid: str) -> dict:
    """No-op task that simulates pipeline processing.

    Accepts an observation UUID, does no actual processing,
    and returns a completion result. Used to verify the Celery
    task chain works end-to-end.
    """
    return {
        "observation_uuid": observation_uuid,
        "status": "completed",
    }
