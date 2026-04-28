from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.modules.ppt.dependencies import get_ppt_service
from app.modules.ppt.schemas import PptTaskCreateRequest, PptTaskSchema
from app.modules.ppt.service import PptService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.post(
    "/tasks",
    response_model=ApiResponse[PptTaskSchema],
    summary="创建 HTML PPT 任务",
)
async def create_ppt_task(
    payload: PptTaskCreateRequest,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> ApiResponse[PptTaskSchema]:
    return ApiResponse.success(ppt_service.create_task(payload))


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[PptTaskSchema],
    summary="获取 HTML PPT 任务",
)
async def get_ppt_task(
    task_id: str,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> ApiResponse[PptTaskSchema]:
    return ApiResponse.success(ppt_service.get_task(task_id))


@router.post(
    "/tasks/{task_id}/run",
    response_model=ApiResponse[PptTaskSchema],
    summary="执行 HTML PPT 任务",
)
async def run_ppt_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> ApiResponse[PptTaskSchema]:
    task = ppt_service.run_task(task_id)
    if task.status == "succeeded" and task.artifact_path is not None:
        background_tasks.add_task(ppt_service.export_pptx, task_id)
    return ApiResponse.success(task)


@router.post(
    "/tasks/{task_id}/export-pptx",
    response_model=ApiResponse[PptTaskSchema],
    summary="导出 HTML PPT 为 PPTX",
)
async def export_pptx_task(
    task_id: str,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> ApiResponse[PptTaskSchema]:
    return ApiResponse.success(ppt_service.export_pptx(task_id))


@router.get(
    "/tasks/{task_id}/preview",
    summary="预览生成后的 HTML PPT",
)
async def preview_ppt_task(
    task_id: str,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> FileResponse:
    task = ppt_service.get_task(task_id)
    if task.artifact_path is None:
        raise HTTPException(status_code=404, detail="PPT artifact not found")
    return FileResponse(task.artifact_path, media_type="text/html")


@router.get(
    "/tasks/{task_id}/download-pptx",
    summary="下载导出的 PPTX",
)
async def download_pptx_task(
    task_id: str,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> FileResponse:
    task = ppt_service.get_task(task_id)
    if task.pptx_path is None:
        if task.pptx_status in {"pending", "running"}:
            raise HTTPException(status_code=409, detail="PPTX artifact is still being generated")
        raise HTTPException(status_code=404, detail="PPTX artifact not found")
    return FileResponse(
        task.pptx_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{task.title or task.topic}.pptx",
    )
