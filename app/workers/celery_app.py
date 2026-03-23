from celery import Celery

from app.core.config import get_settings


settings = get_settings()
celery_app = Celery(
    "poacher_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_routes = {"app.workers.tasks.run_scrape_task": {"queue": "scrape"}}
