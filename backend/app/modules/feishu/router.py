from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.schemas import FeishuCardSchema
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
