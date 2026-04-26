from __future__ import annotations

from app.modules.rag.repository import RagRepository
from app.modules.rag.service import RagService


def get_rag_repository() -> RagRepository:
    return RagRepository()


def get_rag_service() -> RagService:
    return RagService(repository=get_rag_repository())
