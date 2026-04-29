from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.modules.ppt.repository import PptRepository
from app.modules.ppt.service import PptService
from app.services.llm_client import LlmClient
from app.services.pptx_export_service import PptxExportService

_ppt_service: PptService | None = None


def get_ppt_service() -> PptService:
    global _ppt_service
    if _ppt_service is None:
        _ppt_service = PptService(
            PptRepository(),
            llm_client=LlmClient(),
            export_service=PptxExportService(),
            generated_root=Path(get_settings().GENERATED_ROOT),
        )
    return _ppt_service
