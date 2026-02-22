from celery import Celery

from shared.config import settings

celery_app = Celery(
    "explore_universe",
    broker=settings.redis_url,
    backend=settings.celery_result_backend_url,
)

celery_app.autodiscover_tasks(["pipeline.tasks"])
