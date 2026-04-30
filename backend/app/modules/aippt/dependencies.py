from __future__ import annotations

from app.config import get_settings
from app.modules.aippt.file_parser import FileParser
from app.modules.aippt.image_generator import GPTImageGenerator
from app.modules.aippt.job_store import JobStore
from app.modules.aippt.llm_client import DeepSeekAIPPTClient
from app.modules.aippt.ppt_master_runner import PPTMasterRunner
from app.modules.aippt.service import AIPPTService


def get_aippt_service() -> AIPPTService:
    settings = get_settings()
    return AIPPTService(
        settings=settings,
        llm_client=DeepSeekAIPPTClient(settings),
        runner=PPTMasterRunner(settings.AIPPT_VENDOR_PATH),
        parser=FileParser(settings.AIPPT_VENDOR_PATH),
        job_store=JobStore(
            jobs_root=settings.AIPPT_STORAGE_PATH / "jobs",
            uploads_root=settings.AIPPT_UPLOADS_PATH,
            projects_root=settings.AIPPT_PROJECTS_PATH,
            exports_root=settings.AIPPT_EXPORTS_PATH,
        ),
        image_generator=GPTImageGenerator(settings),
    )
