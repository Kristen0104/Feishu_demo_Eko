from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.schemas import (
    CanvasBoardTaskCreateRequest,
    CanvasBoardTaskSchema,
    CanvasSessionSchema,
)
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


@router.post(
    "/board/tasks",
    response_model=ApiResponse[CanvasBoardTaskSchema],
    summary="创建飞书画板任务",
)
async def create_board_task(
    payload: CanvasBoardTaskCreateRequest,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasBoardTaskSchema]:
    return ApiResponse.success(canvas_service.create_board_task(payload))


@router.get(
    "/board/tasks/{task_id}",
    response_model=ApiResponse[CanvasBoardTaskSchema],
    summary="获取飞书画板任务",
)
async def get_board_task(
    task_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasBoardTaskSchema]:
    return ApiResponse.success(canvas_service.get_board_task(task_id))


@router.post(
    "/board/tasks/{task_id}/run",
    response_model=ApiResponse[CanvasBoardTaskSchema],
    summary="执行飞书画板任务",
)
async def run_board_task(
    task_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasBoardTaskSchema]:
    return ApiResponse.success(canvas_service.run_board_task(task_id))
