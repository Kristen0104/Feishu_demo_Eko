from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.modules.rag.dependencies import get_rag_service
from app.modules.rag.file_parser import parse_rag_upload
from app.modules.rag.schemas import RagFileCreateRequest, RagFileSchema, RagSearchResponse
from app.modules.rag.service import RagService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/files",
    response_model=ApiResponse[list[RagFileSchema]],
    summary="RAG 文件列表骨架",
)
async def list_rag_files(
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> ApiResponse[list[RagFileSchema]]:
    return ApiResponse.success(await rag_service.list_files())


@router.delete(
    "/files/{file_id}",
    response_model=ApiResponse[bool],
    summary="删除 RAG 文件及其向量块",
)
async def delete_rag_file(
    file_id: str,
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> ApiResponse[bool]:
    deleted = await rag_service.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="RAG file not found")
    return ApiResponse.success(True)


@router.post(
    "/files",
    response_model=ApiResponse[RagFileSchema],
    summary="RAG 文件入库",
)
async def ingest_rag_file(
    payload: RagFileCreateRequest,
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> ApiResponse[RagFileSchema]:
    return ApiResponse.success(await rag_service.ingest_file(payload))


@router.post(
    "/files/upload",
    response_model=ApiResponse[RagFileSchema],
    summary="RAG 文件上传解析入库",
)
async def upload_rag_file(
    rag_service: Annotated[RagService, Depends(get_rag_service)],
    file: UploadFile = File(...),
    source: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
) -> ApiResponse[RagFileSchema]:
    content = await file.read()
    try:
        parsed = parse_rag_upload(file.filename or "upload.txt", content)
        parsed_metadata = _parse_metadata(metadata)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not parsed.text.strip():
        raise HTTPException(status_code=400, detail="Uploaded file did not contain extractable text.")

    payload = RagFileCreateRequest(
        filename=parsed.filename,
        source=source or f"browser-upload://{parsed.filename}",
        content=parsed.text,
        metadata={
            **parsed_metadata,
            "file_type": parsed.file_type,
            "upload_filename": parsed.filename,
            "content_length": len(parsed.text),
        },
    )
    return ApiResponse.success(await rag_service.ingest_file(payload))


@router.get(
    "/search",
    response_model=ApiResponse[RagSearchResponse],
    summary="RAG 知识库检索",
)
async def search_rag(
    rag_service: Annotated[RagService, Depends(get_rag_service)],
    query: str = Query(min_length=1),
    limit: int = Query(default=8, ge=1, le=20),
) -> ApiResponse[RagSearchResponse]:
    return ApiResponse.success(RagSearchResponse(query=query, results=await rag_service.search(query, limit=limit)))


def _parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("metadata must be a JSON object") from exc
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object")
    return value
