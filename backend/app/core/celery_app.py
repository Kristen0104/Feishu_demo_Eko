from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "eko_aippt",
    broker=settings.CELERY_EFFECTIVE_BROKER_URL,
    backend=settings.CELERY_EFFECTIVE_RESULT_BACKEND,
)
celery_app.conf.update(
    task_default_queue=settings.CELERY_TASK_QUEUE,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
