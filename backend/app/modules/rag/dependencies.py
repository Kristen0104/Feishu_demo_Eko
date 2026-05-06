from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.rag.repository import RagRepository
from app.modules.rag.service import RagService


def get_rag_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> RagRepository:
    return RagRepository(db)


def get_rag_service(repository: Annotated[RagRepository, Depends(get_rag_repository)]) -> RagService:
    return RagService(repository=repository)
