from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.schemas import CanvasSessionSchema
from app.modules.canvas.service import CanvasService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[CanvasSessionSchema],
    summary="Canvas 会话骨架",
)
async def get_canvas_session(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasSessionSchema]:
    return ApiResponse.success(canvas_service.get_session(session_id))
