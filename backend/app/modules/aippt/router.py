from __future__ import annotations

import inspect
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from starlette.datastructures import UploadFile

from app.modules.aippt.dependencies import get_aippt_service
from app.modules.aippt.schemas import PPTDesignModeOption, PPTGenerationRequest, PPTJobSchema
from app.modules.aippt.service import AIPPTService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/design-modes",
    response_model=ApiResponse[list[PPTDesignModeOption]],
    summary="获取 PPT 生成模式选项",
)
async def list_design_modes() -> ApiResponse[list[PPTDesignModeOption]]:
    return ApiResponse.success(
        [
            PPTDesignModeOption(
                mode="template",
                label="模板",
                description="使用稳定模板布局生成 PPT，速度更快、结果更可控。",
            ),
            PPTDesignModeOption(
                mode="free_design",
                label="自由设计",
                description="逐页自由设计并可使用生图能力，适合更强视觉表现。",
            ),
        ]
    )


@router.post(
    "/generate",
    response_model=ApiResponse[PPTJobSchema],
    summary="创建 PPT 生成任务",
)
async def generate_ppt(
    request: Request,
    aippt_service: Annotated[AIPPTService, Depends(get_aippt_service)],
) -> ApiResponse[PPTJobSchema]:
    payload, upload_filename, upload_bytes, image_uploads = await _parse_generation_request(request)
    _validate_generation_sources(payload, upload_filename)
    create_kwargs = {
        "upload_filename": upload_filename,
        "upload_bytes": upload_bytes,
    }
    if "image_uploads" in inspect.signature(aippt_service.create_job_from_request).parameters:
        create_kwargs["image_uploads"] = image_uploads
    job = aippt_service.create_job_from_request(payload, **create_kwargs)
    aippt_service.enqueue_job(job.job_id)
    return ApiResponse.success(job)


@router.get(
    "/jobs/{job_id}",
    response_model=ApiResponse[PPTJobSchema],
    summary="查询 PPT 任务状态",
)
async def get_ppt_job(
    job_id: str,
    aippt_service: Annotated[AIPPTService, Depends(get_aippt_service)],
) -> ApiResponse[PPTJobSchema]:
    return ApiResponse.success(aippt_service.get_job(job_id))


@router.get(
    "/preview/{job_id}",
    response_model=ApiResponse[dict],
    summary="获取 PPT 预览结构",
)
async def get_ppt_preview(
    job_id: str,
    aippt_service: Annotated[AIPPTService, Depends(get_aippt_service)],
) -> ApiResponse[dict]:
    return ApiResponse.success(aippt_service.get_preview(job_id))


@router.get(
    "/preview/{job_id}/slides/{slide_number}",
    summary="获取 PPT 单页 SVG 预览",
)
async def get_ppt_slide_preview(
    job_id: str,
    slide_number: int,
    aippt_service: Annotated[AIPPTService, Depends(get_aippt_service)],
) -> FileResponse:
    path = aippt_service.get_slide_path(job_id, slide_number)
    return Response(
        content=path.read_text(encoding="utf-8"),
        media_type="image/svg+xml; charset=utf-8",
    )


@router.get(
    "/files/{job_id}",
    summary="下载生成的 PPTX 文件",
)
async def download_ppt(
    job_id: str,
    aippt_service: Annotated[AIPPTService, Depends(get_aippt_service)],
) -> FileResponse:
    path = aippt_service.get_download_path(job_id)
    return FileResponse(
        path=path,
        filename=f"{job_id}.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


async def _parse_generation_request(
    request: Request,
) -> tuple[PPTGenerationRequest, str | None, bytes | None, list[tuple[str, bytes]]]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = PPTGenerationRequest.model_validate(await request.json())
        return payload, None, None, []

    form = await request.form()
    file_value = form.get("file")
    upload_filename: str | None = None
    upload_bytes: bytes | None = None
    image_uploads: list[tuple[str, bytes]] = []

    if isinstance(file_value, UploadFile) and file_value.filename:
        upload_filename = file_value.filename
        upload_bytes = await file_value.read()

    for image_value in form.getlist("image_files"):
        if isinstance(image_value, UploadFile) and image_value.filename:
            image_uploads.append((image_value.filename, await image_value.read()))

    payload = PPTGenerationRequest(
        topic=_optional_string(form.get("topic")),
        page_count=int(form.get("page_count", 6)),
        style=str(form.get("style", "clean_business")),
        design_mode=str(form.get("design_mode", "template")),
        source_url=_optional_string(form.get("source_url")),
    )
    return payload, upload_filename, upload_bytes, image_uploads


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_generation_sources(payload: PPTGenerationRequest, upload_filename: str | None) -> None:
    if payload.topic or payload.source_url or upload_filename:
        return
    raise HTTPException(status_code=422, detail="Either topic, source_url, or file must be provided.")
