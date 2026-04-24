"""
会话管理 API 模块
提供会话的创建、列表、更新、删除接口（待实现）
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.schemas import (
    SessionCreate, SessionUpdate, SessionResponse, SessionListResponse
)

router = APIRouter()


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement session listing
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement session creation
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    session_data: SessionUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement session update
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement session deletion
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
