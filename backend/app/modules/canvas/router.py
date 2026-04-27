from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.schemas import (
    BoardPatchSchema,
    BoardChangeSchema,
    BoardSessionSchema,
    CanvasExportResultSchema,
    CanvasExportRequestSchema,
    CanvasMermaidImportRequestSchema,
    CanvasMermaidImportResultSchema,
    CanvasPublishResultSchema,
    CanvasGenerationRequestSchema,
    CanvasRefreshReviewSchema,
    CanvasSessionDetailSchema,
    CanvasSessionSchema,
    EkoWorkingBoardSchema,
    FeishuSourceBoardSchema,
    MergeResolutionRequestSchema,
    MergeReviewRequestSchema,
    MergeReviewSchema,
)
from app.modules.feishu.schemas import FeishuBoardElementMappingSchema
from app.modules.canvas.service import CanvasService
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.schemas import FeishuDocumentResolveRequestSchema
from app.modules.feishu.service import FeishuService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[CanvasSessionSchema],
    summary="Canvas 会话骨架",
)
async def get_canvas_session(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasSessionSchema]:
    return ApiResponse.success(canvas_service.get_session(session_id))


@router.get(
    "/sessions/{session_id}/detail",
    response_model=ApiResponse[CanvasSessionDetailSchema],
    summary="Canvas 会话详情",
)
async def get_canvas_session_detail(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasSessionDetailSchema]:
    return ApiResponse.success(canvas_service.get_session_detail(session_id))


@router.get(
    "/sessions/{session_id}/source-board",
    response_model=ApiResponse[FeishuSourceBoardSchema],
    summary="Canvas 源画板",
)
async def get_canvas_source_board(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[FeishuSourceBoardSchema]:
    return ApiResponse.success(canvas_service.get_feishu_source_board(session_id))


@router.get(
    "/sessions/{session_id}/mappings",
    response_model=ApiResponse[list[FeishuBoardElementMappingSchema]],
    summary="Canvas 元素映射",
)
async def get_canvas_element_mappings(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[list[FeishuBoardElementMappingSchema]]:
    detail = canvas_service.get_session_detail(session_id)
    return ApiResponse.success(detail.element_mappings)


@router.post(
    "/sessions/{session_id}/import-feishu-document",
    response_model=ApiResponse[CanvasSessionDetailSchema],
    summary="从飞书文档导入首个画板到 Canvas 会话",
)
async def import_canvas_session_from_feishu_document(
    session_id: str,
    payload: FeishuDocumentResolveRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[CanvasSessionDetailSchema]:
    imported = feishu_service.resolve_document_whiteboard_import_payload(
        share_url=payload.share_url,
        session_id=session_id,
    )
    return ApiResponse.success(canvas_service.ingest_feishu_board(session_id, imported))


@router.post(
    "/sessions/{session_id}/import-mermaid",
    response_model=ApiResponse[CanvasMermaidImportResultSchema],
    summary="将 Mermaid 语法导入当前 Canvas 会话对应的飞书白板",
)
async def import_canvas_session_from_mermaid(
    session_id: str,
    payload: CanvasMermaidImportRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[CanvasMermaidImportResultSchema]:
    return ApiResponse.success(
        canvas_service.import_mermaid_board(
            session_id=session_id,
            payload=payload,
            feishu_service=feishu_service,
        )
    )


@router.post(
    "/sessions/{session_id}/refresh-feishu-document",
    response_model=ApiResponse[CanvasSessionDetailSchema],
    summary="刷新 Canvas 会话关联的飞书文档画板",
)
async def refresh_canvas_session_from_feishu_document(
    session_id: str,
    payload: FeishuDocumentResolveRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[CanvasSessionDetailSchema]:
    imported = feishu_service.resolve_document_whiteboard_import_payload(
        share_url=payload.share_url,
        session_id=session_id,
    )
    return ApiResponse.success(canvas_service.ingest_feishu_board(session_id, imported))


@router.post(
    "/sessions/{session_id}/refresh-feishu-document-review",
    response_model=ApiResponse[CanvasRefreshReviewSchema],
    summary="刷新飞书文档并在冲突时自动生成合并审查",
)
async def refresh_canvas_session_from_feishu_document_and_review(
    session_id: str,
    payload: FeishuDocumentResolveRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
) -> ApiResponse[CanvasRefreshReviewSchema]:
    imported = feishu_service.resolve_document_whiteboard_import_payload(
        share_url=payload.share_url,
        session_id=session_id,
    )
    return ApiResponse.success(
        canvas_service.refresh_feishu_board_review(session_id, imported)
    )


@router.get(
    "/sessions/{session_id}/state",
    response_model=ApiResponse[BoardSessionSchema],
    summary="Canvas 会话状态",
)
async def get_canvas_session_state(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[BoardSessionSchema]:
    return ApiResponse.success(canvas_service.get_board_session(session_id))


@router.get(
    "/sessions/{session_id}/working-board",
    response_model=ApiResponse[EkoWorkingBoardSchema],
    summary="Canvas 工作副本",
)
async def get_canvas_working_board(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[EkoWorkingBoardSchema]:
    return ApiResponse.success(canvas_service.get_working_board(session_id))


@router.get(
    "/sessions/{session_id}/changes",
    response_model=ApiResponse[list[BoardChangeSchema]],
    summary="Canvas 变更历史",
)
async def get_canvas_changes(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[list[BoardChangeSchema]]:
    return ApiResponse.success(canvas_service.list_changes(session_id))


@router.post(
    "/sessions/{session_id}/changes",
    response_model=ApiResponse[EkoWorkingBoardSchema],
    summary="应用 Canvas 变更",
)
async def apply_canvas_change(
    session_id: str,
    payload: BoardChangeSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[EkoWorkingBoardSchema]:
    return ApiResponse.success(canvas_service.apply_change(session_id, payload))


@router.post(
    "/sessions/{session_id}/generate",
    response_model=ApiResponse[BoardPatchSchema],
    summary="生成画板补丁",
)
def generate_canvas_patch(
    session_id: str,
    payload: CanvasGenerationRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[BoardPatchSchema]:
    return ApiResponse.success(canvas_service.generate_patch(session_id, payload))


@router.post(
    "/sessions/{session_id}/apply-patch",
    response_model=ApiResponse[CanvasSessionDetailSchema],
    summary="应用 AI 画板补丁",
)
async def apply_canvas_patch(
    session_id: str,
    payload: BoardPatchSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasSessionDetailSchema]:
    return ApiResponse.success(canvas_service.apply_patch(session_id, payload))


@router.post(
    "/sessions/{session_id}/export-feishu-board",
    response_model=ApiResponse[CanvasExportResultSchema],
    summary="导出当前 Canvas 会话到飞书画板适配格式",
)
async def export_canvas_session_to_feishu_board(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
    payload: CanvasExportRequestSchema | None = None,
) -> ApiResponse[CanvasExportResultSchema]:
    return ApiResponse.success(
        canvas_service.export_feishu_board(session_id, feishu_service, payload)
    )


@router.post(
    "/sessions/{session_id}/publish-feishu-board",
    response_model=ApiResponse[CanvasPublishResultSchema],
    summary="发布当前 Canvas 会话到飞书画板",
)
async def publish_canvas_session_to_feishu_board(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
    payload: CanvasExportRequestSchema | None = None,
) -> ApiResponse[CanvasPublishResultSchema]:
    return ApiResponse.success(
        canvas_service.publish_feishu_board(session_id, feishu_service, payload)
    )


@router.post(
    "/sessions/{session_id}/merge-review",
    response_model=ApiResponse[MergeReviewSchema],
    summary="创建合并审查",
)
async def create_merge_review(
    session_id: str,
    payload: MergeReviewRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[MergeReviewSchema]:
    return ApiResponse.success(canvas_service.create_merge_review(session_id, payload))


@router.get(
    "/sessions/{session_id}/merge-reviews",
    response_model=ApiResponse[list[MergeReviewSchema]],
    summary="列出 Canvas 会话的合并审查",
)
async def list_merge_reviews(
    session_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[list[MergeReviewSchema]]:
    return ApiResponse.success(canvas_service.list_merge_reviews(session_id))


@router.get(
    "/sessions/{session_id}/merge-reviews/{review_id}",
    response_model=ApiResponse[MergeReviewSchema],
    summary="读取合并审查状态",
)
async def get_merge_review(
    session_id: str,
    review_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[MergeReviewSchema]:
    return ApiResponse.success(canvas_service.get_merge_review(session_id, review_id))


@router.post(
    "/sessions/{session_id}/merge-resolve",
    response_model=ApiResponse[CanvasSessionDetailSchema],
    summary="解决 Canvas 合并冲突",
)
async def resolve_merge_review(
    session_id: str,
    payload: MergeResolutionRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasSessionDetailSchema]:
    return ApiResponse.success(canvas_service.resolve_merge_review(session_id, payload))
