from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from app.config import settings
from app.modules.feishu.client import FeishuPermissionError
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.schemas import (
    FeishuCardSchema,
    PublishToFeishuRequest,
    PublishToFeishuResponse,
    ImportTaskStatus,
)
from app.modules.feishu.service import FeishuService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/cards/{card_id}",
    response_model=ApiResponse[FeishuCardSchema],
    summary="飞书卡片骨架",
)
async def get_feishu_card(
    card_id: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuCardSchema]:
    return ApiResponse.success(feishu_service.get_card(card_id))


@router.post(
    "/sync/publish",
    response_model=ApiResponse[PublishToFeishuResponse],
    summary="发布Markdown文档到飞书",
)
async def publish_to_feishu(
    request: PublishToFeishuRequest,
    background_tasks: BackgroundTasks,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[PublishToFeishuResponse]:
    """将编辑好的 Markdown 文档发布为飞书文档，并可选写入多维表格

    流程：
    1. 后端接收 Markdown，创建后台任务
    2. 立即返回接受状态，前端轮询或等待 Redis 通知
    3. 后台异步执行导入任务，轮询等待完成
    4. 完成后写入多维表格，通过 Pub/Sub 通知前端
    """
    try:
        ticket = await feishu_service.create_import_ticket(
            request.markdown_content,
            request.title,
        )
    except FeishuPermissionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 使用配置的默认值（如果请求中未提供）
    app_token = request.app_token or settings.FEISHU_BITABLE_APP_TOKEN or None
    table_id = request.table_id or settings.FEISHU_BITABLE_TABLE_ID or None

    # 添加后台任务处理后续流程
    background_tasks.add_task(
        feishu_service.publish_markdown_background,
        session_id=request.session_id,
        title=request.title,
        markdown_content=request.markdown_content,
        app_token=app_token,
        table_id=table_id,
        ticket=ticket,
    )

    return ApiResponse.success(PublishToFeishuResponse(
        ticket=ticket,
        status="processing",
    ))


@router.get(
    "/sync/status/{ticket}",
    response_model=ApiResponse[ImportTaskStatus],
    summary="查询导入任务状态",
)
async def get_import_status(
    ticket: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[ImportTaskStatus]:
    """轮询导入任务状态（备选方案，前端也可选择 Redis WebSocket 订阅）"""
    status = feishu_service.get_import_status(ticket)
    return ApiResponse.success(ImportTaskStatus(**status))
