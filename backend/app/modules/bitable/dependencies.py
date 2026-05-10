from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.bitable.openapi_adapter import BitableOpenApiAdapter
from app.modules.bitable.repository import BitableRepository
from app.modules.bitable.service import BitableService
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.dependencies import get_feishu_client


def get_bitable_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> BitableRepository:
    return BitableRepository(db)


def get_bitable_service(
    repository: Annotated[BitableRepository, Depends(get_bitable_repository)],
    feishu_client: Annotated[FeishuClient, Depends(get_feishu_client)],
) -> BitableService:
    return BitableService(repository, adapter=BitableOpenApiAdapter(feishu_client=feishu_client))
