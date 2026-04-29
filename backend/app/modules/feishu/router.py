from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.config import settings
from app.modules.feishu.client import FeishuPermissionError
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.schemas import (
    FeishuBoardCreateNotesRequest,
    FeishuBoardCreateNotesSchema,
    FeishuBoardDeleteRequest,
    FeishuBoardDeleteSchema,
    FeishuBoardImageSchema,
    FeishuBoardImportRequest,
    FeishuBoardImportSchema,
    FeishuBoardNodesSchema,
    FeishuBoardUpdateRequest,
    FeishuBoardUpdateSchema,
    FeishuCardSchema,
    ImportTaskStatus,
    PublishToFeishuRequest,
    PublishToFeishuResponse,
)
from app.modules.feishu.service import FeishuService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get("/cards/{card_id}", response_model=ApiResponse[FeishuCardSchema], summary="飞书卡片骨架")
async def get_feishu_card(
    card_id: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuCardSchema]:
    return ApiResponse.success(feishu_service.get_card(card_id))


@router.post("/board/import", response_model=ApiResponse[FeishuBoardImportSchema], summary="导入图表到飞书画板")
async def import_board_diagram(
    payload: FeishuBoardImportRequest,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardImportSchema]:
    return ApiResponse.success(feishu_service.import_diagram(payload))


@router.post("/board/create-notes", response_model=ApiResponse[FeishuBoardCreateNotesSchema], summary="创建飞书画板节点")
async def create_board_notes(
    payload: FeishuBoardCreateNotesRequest,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardCreateNotesSchema]:
    return ApiResponse.success(feishu_service.create_notes(payload))


@router.get("/board/nodes/{whiteboard_id}", response_model=ApiResponse[FeishuBoardNodesSchema], summary="获取飞书画板节点")
async def get_board_nodes(
    whiteboard_id: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
    user_access_token: str | None = None,
) -> ApiResponse[FeishuBoardNodesSchema]:
    return ApiResponse.success(feishu_service.get_board_nodes(whiteboard_id, user_access_token=user_access_token))


@router.get("/board/image/{whiteboard_id}", response_model=ApiResponse[FeishuBoardImageSchema], summary="获取飞书画板图片")
async def get_board_image(
    whiteboard_id: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
    user_access_token: str | None = None,
) -> ApiResponse[FeishuBoardImageSchema]:
    return ApiResponse.success(feishu_service.get_board_image(whiteboard_id, user_access_token=user_access_token))


@router.post("/board/update", response_model=ApiResponse[FeishuBoardUpdateSchema], summary="更新飞书画板内容")
async def update_board(
    payload: FeishuBoardUpdateRequest,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardUpdateSchema]:
    return ApiResponse.success(feishu_service.update_board(payload))


@router.post("/board/delete", response_model=ApiResponse[FeishuBoardDeleteSchema], summary="删除飞书画板节点")
async def delete_board(
    payload: FeishuBoardDeleteRequest,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardDeleteSchema]:
    return ApiResponse.success(feishu_service.delete_board(payload))


@router.post("/sync/publish", response_model=ApiResponse[PublishToFeishuResponse], summary="发布Markdown文档到飞书")
async def publish_to_feishu(
    request: PublishToFeishuRequest,
    background_tasks: BackgroundTasks,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[PublishToFeishuResponse]:
    try:
        ticket = await feishu_service.create_import_ticket(request.markdown_content, request.title)
    except FeishuPermissionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    app_token = request.app_token or settings.FEISHU_BITABLE_APP_TOKEN or None
    table_id = request.table_id or settings.FEISHU_BITABLE_TABLE_ID or None
    background_tasks.add_task(
        feishu_service.publish_markdown_background,
        session_id=request.session_id,
        title=request.title,
        markdown_content=request.markdown_content,
        app_token=app_token,
        table_id=table_id,
        ticket=ticket,
    )
    return ApiResponse.success(PublishToFeishuResponse(ticket=ticket, status="processing"))


@router.get("/sync/status/{ticket}", response_model=ApiResponse[ImportTaskStatus], summary="查询导入任务状态")
async def get_import_status(
    ticket: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[ImportTaskStatus]:
    status = feishu_service.get_import_status(ticket)
    return ApiResponse.success(ImportTaskStatus(**status))
