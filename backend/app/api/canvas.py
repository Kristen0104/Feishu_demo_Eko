"""
Canvas 白板 API 模块
提供画布快照保存、元素更新、版本历史接口（待实现）
"""
# TODO(PRD-2.3): implement creator-only canvas editing, versioning, and realtime mirror sync.
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.schemas import (
    CanvasSnapshotRequest, CanvasUpdateRequest, CanvasResponse, CanvasVersionResponse
)

router = APIRouter()


@router.get("/{session_id}", response_model=CanvasResponse)
async def get_canvas(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement canvas retrieval
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/snapshot")
async def save_canvas_snapshot(
    request: CanvasSnapshotRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement canvas snapshot
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.patch("/elements")
async def update_canvas_elements(
    request: CanvasUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement canvas element update
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/versions")
async def get_canvas_versions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement canvas versions
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
