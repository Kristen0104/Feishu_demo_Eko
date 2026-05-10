from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.bitable.repository import BitableRepository
from app.modules.bitable.service import BitableService


def get_bitable_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> BitableRepository:
    return BitableRepository(db)


def get_bitable_service(repository: Annotated[BitableRepository, Depends(get_bitable_repository)]) -> BitableService:
    return BitableService(repository)
