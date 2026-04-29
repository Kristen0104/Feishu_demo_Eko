from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.modules.ppt.dependencies import get_ppt_service
from app.modules.ppt.schemas import (
    PptDeckCreateRequest,
    PptDeckModifyRequest,
    PptDeckSchema,
    PptExportSchema,
    PptThemeSchema,
)
from app.modules.ppt.service import PptService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.post(
    "/decks",
    response_model=ApiResponse[PptDeckSchema],
    summary="生成 HTML PPT deck",
)
async def create_deck(
    payload: PptDeckCreateRequest,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> ApiResponse[PptDeckSchema]:
    try:
        return ApiResponse.success(ppt_service.create_deck(payload))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/decks/{deck_id}/modify",
    response_model=ApiResponse[PptDeckSchema],
    summary="自然语言修改 PPT deck",
)
async def modify_deck(
    deck_id: str,
    payload: PptDeckModifyRequest,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> ApiResponse[PptDeckSchema]:
    try:
        return ApiResponse.success(ppt_service.modify_deck(deck_id, payload))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/decks/{deck_id}/export",
    response_model=ApiResponse[PptExportSchema],
    summary="导出 PPTX",
)
async def export_deck(
    deck_id: str,
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> ApiResponse[PptExportSchema]:
    try:
        return ApiResponse.success(ppt_service.export_deck(deck_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/themes",
    response_model=ApiResponse[list[PptThemeSchema]],
    summary="获取 PPT 主题",
)
async def list_themes(
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
) -> ApiResponse[list[PptThemeSchema]]:
    return ApiResponse.success(ppt_service.list_themes())
