from __future__ import annotations

from app.config import get_settings
from app.modules.ppt.repository import PptRepository
from app.modules.ppt.service import PptService
from app.services.ppt_html_generate_service import PptHtmlGenerateService
from app.services.pptx_export_service import PptxExportService

_ppt_repository = PptRepository()
_ppt_service: PptService | None = None


def get_ppt_repository() -> PptRepository:
    return _ppt_repository


def get_ppt_service() -> PptService:
    global _ppt_service
    if _ppt_service is None:
        _ppt_service = PptService(
            repository=_ppt_repository,
            generate_service=PptHtmlGenerateService(
                allow_live_llm=get_settings().PPT_USE_LIVE_LLM,
            ),
            export_service=PptxExportService(),
        )
    return _ppt_service
