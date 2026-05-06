from __future__ import annotations

from app.core.celery_app import celery_app
from app.modules.aippt.dependencies import get_aippt_service


@celery_app.task(name="aippt.run_job")
def run_ppt_job(job_id: str) -> None:
    get_aippt_service().run_job(job_id)
