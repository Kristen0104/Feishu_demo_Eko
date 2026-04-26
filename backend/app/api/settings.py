"""
飞书多维表格配置 API 模块
提供 Bitable 连接配置接口（待实现）
"""
# TODO(PRD-4.3): expose configurable Feishu, RAG, and PPT module settings through a dedicated workspace config surface.
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.schemas import (
    BitableConfigRequest, BitableTableResponse, BitableFieldResponse
)

router = APIRouter()


@router.get("/feishu/bitable/tables", response_model=list[BitableTableResponse])
async def get_bitable_tables(
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement bitable tables retrieval
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/feishu/bitable/fields", response_model=list[BitableFieldResponse])
async def get_bitable_fields(
    table_id: str,
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement bitable fields retrieval
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/feishu/bitable/config")
async def set_bitable_config(
    request: BitableConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement bitable config
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
