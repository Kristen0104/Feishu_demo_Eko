from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

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
    "/board/import",
    response_model=ApiResponse[FeishuBoardImportSchema],
    summary="导入图表到飞书画板",
)
async def import_board_diagram(
    payload: FeishuBoardImportRequest,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardImportSchema]:
    return ApiResponse.success(feishu_service.import_diagram(payload))


@router.post(
    "/board/create-notes",
    response_model=ApiResponse[FeishuBoardCreateNotesSchema],
    summary="创建飞书画板节点",
)
async def create_board_notes(
    payload: FeishuBoardCreateNotesRequest,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardCreateNotesSchema]:
    return ApiResponse.success(feishu_service.create_notes(payload))


@router.get(
    "/board/nodes/{whiteboard_id}",
    response_model=ApiResponse[FeishuBoardNodesSchema],
    summary="获取飞书画板节点",
)
async def get_board_nodes(
    whiteboard_id: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
    user_access_token: str | None = None,
) -> ApiResponse[FeishuBoardNodesSchema]:
    return ApiResponse.success(feishu_service.get_board_nodes(whiteboard_id, user_access_token=user_access_token))


@router.get(
    "/board/image/{whiteboard_id}",
    response_model=ApiResponse[FeishuBoardImageSchema],
    summary="获取飞书画板图片",
)
async def get_board_image(
    whiteboard_id: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
    user_access_token: str | None = None,
) -> ApiResponse[FeishuBoardImageSchema]:
    return ApiResponse.success(feishu_service.get_board_image(whiteboard_id, user_access_token=user_access_token))


@router.post(
    "/board/update",
    response_model=ApiResponse[FeishuBoardUpdateSchema],
    summary="更新飞书画板内容",
)
async def update_board(
    payload: FeishuBoardUpdateRequest,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardUpdateSchema]:
    return ApiResponse.success(feishu_service.update_board(payload))


@router.post(
    "/board/delete",
    response_model=ApiResponse[FeishuBoardDeleteSchema],
    summary="删除飞书画板节点",
)
async def delete_board(
    payload: FeishuBoardDeleteRequest,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardDeleteSchema]:
    return ApiResponse.success(feishu_service.delete_board(payload))
