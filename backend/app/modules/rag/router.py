from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.rag.dependencies import get_rag_service
from app.modules.rag.schemas import RagFileSchema
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
    return ApiResponse.success(rag_service.list_files())
