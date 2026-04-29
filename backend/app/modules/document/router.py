"""
Document Router - 文档模块API端点
"""
from __future__ import annotations

import json
from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.core.llm_client import LLMRequestError
from app.modules.document.dependencies import get_document_service
from app.modules.document.service import DocumentService
from app.modules.document.schemas import (
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    DocumentSaveRequest,
    DocumentSaveResponse,
)
from app.shared.responses import ApiResponse

router = APIRouter()


@router.post(
    "/generate",
    response_model=ApiResponse[DocumentGenerationResponse],
    summary="生成文档（非流式）",
)
async def generate_document(
    request: DocumentGenerationRequest,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiResponse[DocumentGenerationResponse]:
    """一次性生成完整文档"""
    try:
        content = await service.generate_document(request)
    except LLMRequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM service rejected the request: {exc.message}",
        ) from exc
    return ApiResponse.success(
        DocumentGenerationResponse(
            session_id=request.session_id,
            status="completed",
            content=content,
        )
    )


@router.post(
    "/generate/stream",
    summary="生成文档（流式输出）",
)
async def generate_document_stream(
    request: DocumentGenerationRequest,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> StreamingResponse:
    """流式输出文档生成过程"""

    async def stream_generator():
        yield (
            f"data: {json.dumps({'session_id': request.session_id, 'status': 'generating'}, ensure_ascii=False)}\n\n"
        )
        try:
            async for chunk in service.generate_document_stream(request):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'status': 'completed'}, ensure_ascii=False)}\n\n"
        except LLMRequestError as exc:
            yield (
                f"data: {json.dumps({'status': 'failed', 'error': f'LLM service rejected the request: {exc.message}'}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/save",
    response_model=ApiResponse[DocumentSaveResponse],
    summary="保存文档并同步到飞书",
)
async def save_document(
    request: DocumentSaveRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiResponse[DocumentSaveResponse]:
    """保存文档，可选同步到飞书"""
    if request.sync_to_feishu:
        # 异步执行同步任务
        background_tasks.add_task(
            service.save_and_sync_document,
            session_id=request.session_id,
            title=request.title,
            content=request.content,
            app_token=request.app_token,
            table_id=request.table_id,
        )
        return ApiResponse.success(
            DocumentSaveResponse(
                session_id=request.session_id,
                status="saving",
                message="正在同步到飞书...",
            )
        )
    else:
        # 仅返回成功（暂不做本地存储）
        return ApiResponse.success(
            DocumentSaveResponse(
                session_id=request.session_id,
                status="saved",
                message="文档已保存",
            )
        )


@router.post(
    "/test/generate",
    response_model=ApiResponse[DocumentGenerationResponse],
    summary="测试：生成模拟文档（不调用LLM）",
)
async def test_generate_document(
    request: DocumentGenerationRequest,
) -> ApiResponse[DocumentGenerationResponse]:
    """测试用：返回模拟的文档内容，不消耗 LLM token"""
    mock_content = f"""# {request.topic}

## 一、背景介绍

这是一份由 AI 生成的测试文档，用于验证接口流程。

## 二、主要内容

根据您的需求："{request.requirement}"

我们可以按以下步骤展开：

1. 第一步：明确目标
2. 第二步：制定计划
3. 第三步：执行实施
4. 第四步：总结回顾

## 三、总结

本文档类型为 {request.document_type.value}，采用 {request.tone} 语气。

---

*本文档为测试模拟内容，未实际调用 LLM。*
"""
    return ApiResponse.success(
        DocumentGenerationResponse(
            session_id=request.session_id,
            status="completed",
            content=mock_content,
        )
    )


@router.post(
    "/test/save",
    response_model=ApiResponse[DocumentSaveResponse],
    summary="测试：保存文档（不同步飞书）",
)
async def test_save_document(
    request: DocumentSaveRequest,
) -> ApiResponse[DocumentSaveResponse]:
    """测试用：保存文档但不调用飞书 API"""
    return ApiResponse.success(
        DocumentSaveResponse(
            session_id=request.session_id,
            status="saved",
            message="文档已保存（测试模式，未同步飞书）",
        )
    )
