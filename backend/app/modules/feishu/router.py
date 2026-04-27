from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
    FeishuBoardPublishResultSchema,
    FeishuBoardMermaidImportRequestSchema,
    FeishuBoardSyntaxImportRequestSchema,
    FeishuBoardSyntaxImportResultSchema,
    FeishuCardSchema,
    FeishuDocumentBlocksSchema,
    FeishuDocumentContentSchema,
    FeishuDocumentResolveRequestSchema,
    FeishuDocumentWhiteboardImportRequestSchema,
    FeishuDocumentWhiteboardNodesSchema,
    FeishuDocumentWhiteboardsDiscoverySchema,
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
    "/boards/import",
    response_model=ApiResponse[FeishuBoardAdapterPayloadSchema],
    summary="飞书画板导入",
)
async def import_feishu_board(
    payload: FeishuBoardAdapterPayloadSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardAdapterPayloadSchema]:
    return ApiResponse.success(feishu_service.import_board(payload))


@router.post(
    "/boards/export",
    response_model=ApiResponse[FeishuBoardAdapterPayloadSchema],
    summary="飞书画板导出",
)
async def export_feishu_board(
    payload: FeishuBoardAdapterPayloadSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardAdapterPayloadSchema]:
    return ApiResponse.success(feishu_service.export_board(payload))


@router.post(
    "/boards/publish",
    response_model=ApiResponse[FeishuBoardPublishResultSchema],
    summary="飞书画板发布",
)
async def publish_feishu_board(
    payload: FeishuBoardAdapterPayloadSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardPublishResultSchema]:
    return ApiResponse.success(feishu_service.publish_board(payload))


@router.post(
    "/boards/{whiteboard_id}/syntax-import",
    response_model=ApiResponse[FeishuBoardSyntaxImportResultSchema],
    summary="飞书画板 PlantUML/Mermaid 语法导入",
)
async def import_feishu_whiteboard_syntax(
    whiteboard_id: str,
    payload: FeishuBoardSyntaxImportRequestSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardSyntaxImportResultSchema]:
    return ApiResponse.success(
        feishu_service.import_whiteboard_syntax(
            whiteboard_id=whiteboard_id,
            payload=payload,
        )
    )


@router.post(
    "/boards/{whiteboard_id}/mermaid-import",
    response_model=ApiResponse[FeishuBoardSyntaxImportResultSchema],
    summary="飞书画板 Mermaid 语法导入",
)
async def import_feishu_whiteboard_mermaid(
    whiteboard_id: str,
    payload: FeishuBoardMermaidImportRequestSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardSyntaxImportResultSchema]:
    return ApiResponse.success(
        feishu_service.import_mermaid_whiteboard_syntax(
            whiteboard_id=whiteboard_id,
            payload=payload,
        )
    )


@router.post(
    "/documents/resolve",
    response_model=ApiResponse[FeishuDocumentContentSchema],
    summary="飞书文档解析",
)
async def resolve_feishu_document(
    payload: FeishuDocumentResolveRequestSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuDocumentContentSchema]:
    return ApiResponse.success(feishu_service.resolve_document_content(payload.share_url))


@router.post(
    "/documents/resolve-whiteboards",
    response_model=ApiResponse[FeishuDocumentWhiteboardsDiscoverySchema],
    summary="飞书文档画板发现",
)
async def resolve_feishu_document_whiteboards(
    payload: FeishuDocumentResolveRequestSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuDocumentWhiteboardsDiscoverySchema]:
    return ApiResponse.success(
        feishu_service.discover_document_whiteboards(payload.share_url)
    )


@router.post(
    "/documents/resolve-whiteboard-nodes",
    response_model=ApiResponse[FeishuDocumentWhiteboardNodesSchema],
    summary="飞书文档首个画板节点解析",
)
async def resolve_feishu_document_whiteboard_nodes(
    payload: FeishuDocumentResolveRequestSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuDocumentWhiteboardNodesSchema]:
    return ApiResponse.success(
        feishu_service.resolve_document_whiteboard_nodes(payload.share_url)
    )


@router.post(
    "/documents/resolve-whiteboard-import",
    response_model=ApiResponse[FeishuBoardAdapterPayloadSchema],
    summary="飞书文档首个画板转导入载荷",
)
async def resolve_feishu_document_whiteboard_import(
    payload: FeishuDocumentWhiteboardImportRequestSchema,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuBoardAdapterPayloadSchema]:
    return ApiResponse.success(
        feishu_service.resolve_document_whiteboard_import_payload(
            share_url=payload.share_url,
            session_id=payload.session_id,
        )
    )


@router.get(
    "/documents/{document_id}/blocks",
    response_model=ApiResponse[FeishuDocumentBlocksSchema],
    summary="飞书文档 blocks 解析",
)
async def get_feishu_document_blocks(
    document_id: str,
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[FeishuDocumentBlocksSchema]:
    return ApiResponse.success(feishu_service.get_document_blocks(document_id))
