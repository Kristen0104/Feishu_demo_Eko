from __future__ import annotations

import json
import time
from copy import deepcopy
import logging

from fastapi import HTTPException

from app.modules.canvas.ai_service import CanvasAiServiceProtocol
from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import (
    BoardPatchSchema,
    BoardChangeSchema,
    BoardSessionSchema,
    CanvasExportResultSchema,
    CanvasExportRequestSchema,
    CanvasMermaidImportRequestSchema,
    CanvasRefreshReviewSchema,
    CanvasPublishResultSchema,
    CanvasMermaidImportResultSchema,
    CanvasGenerationRequestSchema,
    CanvasSessionDetailSchema,
    CanvasSessionSchema,
    EkoWorkingBoardSchema,
    FeishuSourceBoardSchema,
    GenerationInfoSchema,
    MergeResolutionRequestSchema,
    MergeReviewRequestSchema,
    MergeReviewSchema,
)
from app.modules.canvas.style_templates import apply_canvas_style_template
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
    FeishuDocumentContentSchema,
)
from app.modules.feishu.service import FeishuService

logger = logging.getLogger(__name__)


class CanvasService:
    def __init__(
        self,
        repository: CanvasRepository,
        ai_service: CanvasAiServiceProtocol | None = None,
    ) -> None:
        # Keep business rules above the repository boundary once canvas state
        # moves beyond this registration-layer stub.
        self._repository = repository
        self._ai_service = ai_service

    def get_session(self, session_id: str) -> CanvasSessionSchema:
        return self._repository.get_session(session_id)

    def get_session_detail(self, session_id: str) -> CanvasSessionDetailSchema:
        return self._repository.get_session_detail(session_id)

    def get_board_session(self, session_id: str) -> BoardSessionSchema:
        return self._repository.get_board_session(session_id)

    def get_feishu_source_board(self, session_id: str) -> FeishuSourceBoardSchema:
        return self._repository.get_feishu_source_board(session_id)

    def get_merge_review(self, session_id: str, review_id: str) -> MergeReviewSchema:
        return self._repository.get_merge_review(session_id, review_id)

    def list_merge_reviews(self, session_id: str) -> list[MergeReviewSchema]:
        return self._repository.list_merge_reviews(session_id)

    def get_working_board(self, session_id: str) -> EkoWorkingBoardSchema:
        return self._repository.get_working_board(session_id)

    def list_changes(self, session_id: str) -> list[BoardChangeSchema]:
        return self._repository.list_recent_changes(session_id)

    def ingest_feishu_board(
        self,
        session_id: str,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> CanvasSessionDetailSchema:
        return self._repository.ingest_feishu_board(session_id, payload)

    def import_mermaid_board(
        self,
        session_id: str,
        payload: CanvasMermaidImportRequestSchema,
        feishu_service: FeishuService,
    ) -> CanvasMermaidImportResultSchema:
        detail = self._repository.get_session_detail(session_id)
        source_metadata = detail.source_board.raw_payload.get("source_metadata", {})
        share_url = str(source_metadata.get("share_url", "")).strip()
        if not share_url:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Cannot refresh Mermaid import without a source share_url",
                    "session_id": session_id,
                },
            )

        feishu_service.import_mermaid_whiteboard_syntax(
            whiteboard_id=detail.source_board.source_board_id,
            payload=payload,
        )
        refreshed_payload = feishu_service.resolve_document_whiteboard_import_payload(
            share_url=share_url,
            session_id=session_id,
        )
        return CanvasMermaidImportResultSchema(
            detail=self._repository.ingest_feishu_board(session_id, refreshed_payload)
        )

    def build_generation_request_from_feishu_document(
        self,
        document: FeishuDocumentContentSchema,
        *,
        user_prompt: str,
    ) -> CanvasGenerationRequestSchema:
        source_metadata = {
            "source_type": "feishu_document",
            "document_token": document.document_token,
            "document_id": document.document_id,
            "title": document.title,
            "share_url": document.share_url,
        }
        return CanvasGenerationRequestSchema(
            generation_mode="full_board",
            chat_context=[
                {
                    "role": "system",
                    "content": f"文档标题: {document.title}",
                },
                {
                    "role": "user",
                    "content": "\n".join(
                        [
                            "请基于以下飞书文档内容生成画板输入：",
                            f"share_url: {document.share_url}",
                            f"document_token: {document.document_token}",
                            f"plain_text:\n{document.plain_text}",
                            f"raw_content:\n{json.dumps(document.raw_content, ensure_ascii=False)}",
                        ]
                    ),
                },
            ],
            user_prompt=user_prompt,
            board_context={
                "source": {
                    "source_type": "feishu_document",
                    "document_token": document.document_token,
                    "document_id": document.document_id,
                    "share_url": document.share_url,
                },
                "source_document": document.model_dump(mode="json"),
            },
            session_metadata={
                "source": source_metadata,
                "session": {
                    "mode": "document_to_canvas_generation",
                    "conversation_id": f"feishu-doc-{document.document_token}",
                    "title": document.title,
                },
            },
            selection_context=None,
        )

    def build_generation_context_from_feishu_document(
        self,
        document: FeishuDocumentContentSchema,
        *,
        user_prompt: str,
    ) -> CanvasGenerationRequestSchema:
        return self.build_generation_request_from_feishu_document(
            document,
            user_prompt=user_prompt,
        )

    def apply_change(
        self,
        session_id: str,
        change: BoardChangeSchema,
    ) -> EkoWorkingBoardSchema:
        return self._repository.apply_change(session_id, change)

    def generate_patch(
        self,
        session_id: str,
        payload: CanvasGenerationRequestSchema,
    ) -> BoardPatchSchema:
        started_at = time.perf_counter()
        if self._ai_service is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Canvas AI provider is not configured",
                    "session_id": session_id,
                },
            )

        try:
            generated_patch = self._ai_service.generate_patch(
                session_id=session_id,
                payload=payload,
            )
            if not self._is_usable_ai_patch(generated_patch, payload):
                raise ValueError("AI returned an empty or incompatible canvas patch")
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            generation_info = self._generation_info_to_dict(
                generated_patch.generation_info
            )
            merged_generation_info = dict(generation_info)
            merged_generation_info["source"] = "ai"
            merged_generation_info["latency_ms"] = elapsed_ms
            normalized_patch = self._normalize_generated_patch_layout(generated_patch)
            return normalized_patch.model_copy(
                update={
                    "generation_info": GenerationInfoSchema.model_validate(
                        merged_generation_info
                    )
                }
            )
        except HTTPException:
            raise
        except Exception as exc:
            reason = str(exc).strip() or exc.__class__.__name__
            logger.exception("Canvas AI generation failed")
            raw_content = getattr(exc, "raw_content", None)
            detail = {
                "message": "Canvas AI generation failed",
                "reason": reason,
                "session_id": session_id,
            }
            if isinstance(raw_content, str) and raw_content:
                detail["raw_model_output"] = raw_content[:12000]
            raise HTTPException(
                status_code=502,
                detail=detail,
            ) from exc

    def apply_patch(
        self,
        session_id: str,
        patch: BoardPatchSchema,
    ) -> CanvasSessionDetailSchema:
        detail = self._repository.get_session_detail(session_id)
        latest_snapshot = self._build_snapshot_from_patch(
            patch=patch,
            current_snapshot=detail.working_board.latest_snapshot,
        )
        change = BoardChangeSchema(
            change_id=f"{session_id}-{patch.patch_id}",
            session_id=session_id,
            change_type="ai_patch",
            actor_type="ai",
            actor_id=f"patch:{patch.patch_id}",
            target_scope=self._target_scope_from_patch(patch),
            payload={
                "patch": patch.model_dump(mode="json"),
                "latest_snapshot": latest_snapshot,
                "crdt_document": latest_snapshot,
                "element_mappings": self._mappings_from_patch(patch),
            },
            base_version=f"v{detail.working_board.latest_version}",
            result_version=f"v{detail.working_board.latest_version + 1}",
        )
        self._repository.apply_change(session_id, change)
        return self._repository.get_session_detail(session_id)

    def create_merge_review(
        self,
        session_id: str,
        payload: MergeReviewRequestSchema,
    ) -> MergeReviewSchema:
        return self._repository.build_merge_review(session_id, payload)

    def resolve_merge_review(
        self,
        session_id: str,
        payload: MergeResolutionRequestSchema,
    ) -> CanvasSessionDetailSchema:
        return self._repository.resolve_merge_review(session_id, payload)

    def refresh_feishu_board_review(
        self,
        session_id: str,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> CanvasRefreshReviewSchema:
        detail = self._repository.ingest_feishu_board(session_id, payload)
        merge_review = None
        if detail.session.sync_state == "conflict":
            merge_review = self._repository.build_merge_review(
                session_id,
                MergeReviewRequestSchema(
                    source_version=detail.source_board.source_version,
                    working_version=detail.working_board.latest_version,
                    conflicts=[],
                ),
            )
        return CanvasRefreshReviewSchema(detail=detail, merge_review=merge_review)

    def export_feishu_board(
        self,
        session_id: str,
        feishu_service: FeishuService,
        payload: CanvasExportRequestSchema | None = None,
    ) -> CanvasExportResultSchema:
        export_request = payload or CanvasExportRequestSchema()
        detail = self._repository.get_session_detail(session_id)
        has_conflicts = detail.session.sync_state == "conflict" or any(
            mapping.mapping_status == "conflicted" for mapping in detail.element_mappings
        )
        if has_conflicts and not export_request.allow_conflicted_export:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Canvas session has unresolved conflicts",
                    "session_id": session_id,
                },
            )
        export_payload = self._repository.build_feishu_export_payload(session_id)
        exported_board = feishu_service.export_board(export_payload)
        export_status = "exported_with_conflicts" if has_conflicts else "exported"
        detail = self._repository.record_sync_export(
            session_id,
            exported_board,
            export_status=export_status,
        )
        return CanvasExportResultSchema(
            export_status=export_status,
            exported_board=exported_board,
            detail=detail,
        )

    def publish_feishu_board(
        self,
        session_id: str,
        feishu_service: FeishuService,
        payload: CanvasExportRequestSchema | None = None,
    ) -> CanvasPublishResultSchema:
        export_result = self.export_feishu_board(session_id, feishu_service, payload)
        publish_result = feishu_service.publish_board(export_result.exported_board)
        detail = self._repository.record_publish_result(session_id, publish_result)
        return CanvasPublishResultSchema(
            export_status=export_result.export_status,
            publish_result=publish_result,
            detail=detail,
        )

    @staticmethod
    def _generation_info_to_dict(generation_info: object) -> dict[str, object]:
        if generation_info is None:
            return {}
        if isinstance(generation_info, dict):
            return dict(generation_info)
        if hasattr(generation_info, "model_dump"):
            dumped = generation_info.model_dump(mode="json")
            return dict(dumped) if isinstance(dumped, dict) else {}
        return {}

    @staticmethod
    def _is_usable_ai_patch(
        patch: BoardPatchSchema,
        payload: CanvasGenerationRequestSchema,
    ) -> bool:
        if payload.generation_mode == "targeted_patch":
            return bool(patch.operations)
        if payload.generation_mode == "full_board":
            return patch.full_board is not None
        return False

    @classmethod
    def _normalize_generated_patch_layout(cls, patch: BoardPatchSchema) -> BoardPatchSchema:
        if patch.generation_mode != "full_board" or not isinstance(patch.full_board, dict):
            return patch
        normalized_board = cls._normalize_full_board_layout(patch.full_board)
        normalized_board = apply_canvas_style_template(
            normalized_board,
            style_plan=patch.style_plan,
            override_existing_styles=True,
        )
        if normalized_board is patch.full_board:
            return patch
        return patch.model_copy(update={"full_board": normalized_board})

    @staticmethod
    def _normalize_full_board_layout(full_board: dict[str, object]) -> dict[str, object]:
        nodes = full_board.get("nodes", [])
        if not isinstance(nodes, list) or len(nodes) < 5:
            return full_board
        node_dicts = [node for node in nodes if isinstance(node, dict) and node.get("id")]
        if len(node_dicts) != len(nodes):
            return full_board

        max_columns = 4
        ordered_ids = CanvasService._ordered_node_ids_for_layout(full_board, node_dicts)
        if len(ordered_ids) != len(node_dicts):
            return full_board

        min_x = min(float(node.get("x", 0) or 0) for node in node_dicts)
        max_x = max(
            float(node.get("x", 0) or 0) + float(node.get("width", 220) or 220)
            for node in node_dicts
        )
        width_span = max_x - min_x
        row_count = len(
            {
                int(round(float(node.get("y", 0) or 0) / 20.0))
                for node in node_dicts
            }
        )
        should_reflow = width_span > 1400 or len(node_dicts) > max_columns or row_count > 1
        if not should_reflow:
            return full_board

        node_by_id = {str(node["id"]): node for node in node_dicts}
        base_x = 120
        base_y = 140
        gap_x = 280
        gap_y = 180

        relaid_out_nodes = []
        for index, node_id in enumerate(ordered_ids):
            row = index // max_columns
            row_offset = index % max_columns
            col = row_offset if row % 2 == 0 else max_columns - 1 - row_offset
            original = dict(node_by_id[node_id])
            original["x"] = base_x + col * gap_x
            original["y"] = base_y + row * gap_y
            relaid_out_nodes.append(original)

        return {
            **full_board,
            "nodes": relaid_out_nodes,
        }

    @staticmethod
    def _ordered_node_ids_for_layout(
        full_board: dict[str, object],
        nodes: list[dict[str, object]],
    ) -> list[str]:
        edges = full_board.get("edges", [])
        if not isinstance(edges, list):
            return []

        node_ids = {str(node["id"]) for node in nodes}
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        indegree: dict[str, int] = {node_id: 0 for node_id in node_ids}

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            source = str(edge.get("from", "")).strip()
            target = str(edge.get("to", "")).strip()
            if source not in node_ids or target not in node_ids:
                continue
            outgoing[source].append(target)
            indegree[target] += 1

        starts = [node_id for node_id, degree in indegree.items() if degree == 0]
        if len(starts) != 1:
            return []

        ordered_ids = []
        current = starts[0]
        seen = set()
        while current and current not in seen:
            ordered_ids.append(current)
            seen.add(current)
            next_nodes = [node_id for node_id in outgoing[current] if node_id not in seen]
            if len(next_nodes) > 1:
                return []
            current = next_nodes[0] if next_nodes else ""

        return ordered_ids if len(ordered_ids) == len(node_ids) else []

    @staticmethod
    def _build_snapshot_from_patch(
        *,
        patch: BoardPatchSchema,
        current_snapshot: dict[str, object],
    ) -> dict[str, object]:
        if patch.generation_mode == "full_board" and patch.full_board is not None:
            return apply_canvas_style_template(
                deepcopy(patch.full_board),
                style_plan=patch.style_plan,
                override_existing_styles=True,
            )

        snapshot = deepcopy(current_snapshot)
        nodes = snapshot.get("nodes", [])
        if not isinstance(nodes, list):
            nodes = []
        edges = snapshot.get("edges", [])
        if not isinstance(edges, list):
            edges = []
        updated_nodes: list[dict[str, object]] = []
        existing_node_ids: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            updated_node = dict(node)
            node_id = str(updated_node.get("id", "")).strip()
            if node_id:
                existing_node_ids.add(node_id)
            for operation in patch.operations:
                if (
                    operation.get("type") == "node.replace"
                    and operation.get("target") == updated_node.get("id")
                ):
                    updated_node["text"] = CanvasService._coerce_replace_content(
                        operation.get("content", updated_node.get("text", ""))
                    )
            updated_nodes.append(updated_node)
        for operation in patch.operations:
            if operation.get("type") != "node.add":
                continue
            raw_node = operation.get("node")
            if not isinstance(raw_node, dict):
                continue
            node_id = str(raw_node.get("id", "")).strip()
            if not node_id or node_id in existing_node_ids:
                continue
            updated_nodes.append(dict(raw_node))
            existing_node_ids.add(node_id)
        snapshot["nodes"] = updated_nodes
        updated_edges: list[dict[str, object]] = []
        existing_edge_ids: set[str] = set()
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            updated_edge = dict(edge)
            edge_id = str(updated_edge.get("id", "")).strip()
            if edge_id:
                existing_edge_ids.add(edge_id)
            updated_edges.append(updated_edge)
        for operation in patch.operations:
            if operation.get("type") != "edge.add":
                continue
            raw_edge = operation.get("edge")
            if not isinstance(raw_edge, dict):
                continue
            edge_id = str(raw_edge.get("id", "")).strip()
            if not edge_id or edge_id in existing_edge_ids:
                continue
            updated_edges.append(dict(raw_edge))
            existing_edge_ids.add(edge_id)
        snapshot["edges"] = updated_edges
        return apply_canvas_style_template(snapshot, style_plan=patch.style_plan)

    @staticmethod
    def _coerce_replace_content(content: object) -> str:
        if isinstance(content, dict):
            for key in ("text", "title", "content"):
                value = content.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return json.dumps(content, ensure_ascii=False)
        return str(content)

    @staticmethod
    def _mappings_from_patch(patch: BoardPatchSchema) -> list[dict[str, object]]:
        mappings: list[dict[str, object]] = []
        if patch.generation_mode == "full_board" and patch.full_board is not None:
            nodes = patch.full_board.get("nodes", [])
            edges = patch.full_board.get("edges", [])
        else:
            nodes = [
                operation.get("node")
                for operation in patch.operations
                if operation.get("type") == "node.add" and isinstance(operation.get("node"), dict)
            ]
            edges = [
                operation.get("edge")
                for operation in patch.operations
                if operation.get("type") == "edge.add" and isinstance(operation.get("edge"), dict)
            ]
        if not isinstance(nodes, list):
            nodes = []
        if not isinstance(edges, list):
            edges = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue
            mappings.append(
                {
                    "source_element_id": f"ai:{patch.patch_id}:{node_id}",
                    "working_element_id": node_id,
                    "element_type": "node",
                    "origin_type": "ai",
                    "mapping_status": "active",
                    "metadata": {"patch_id": patch.patch_id},
                }
            )
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            edge_id = str(edge.get("id", "")).strip()
            if not edge_id:
                continue
            mappings.append(
                {
                    "source_element_id": f"ai:{patch.patch_id}:{edge_id}",
                    "working_element_id": edge_id,
                    "element_type": "edge",
                    "origin_type": "ai",
                    "mapping_status": "active",
                    "metadata": {"patch_id": patch.patch_id},
                }
            )
        return mappings

    @staticmethod
    def _target_scope_from_patch(patch: BoardPatchSchema) -> str:
        if patch.generation_mode == "targeted_patch":
            operations = patch.targeted_patch.get("operations", []) if patch.targeted_patch else []
            if operations and isinstance(operations, list):
                first = operations[0]
                if isinstance(first, dict):
                    if first.get("type") == "node.add":
                        return "board:working"
                    target = str(first.get("target", "")).strip()
                    if target:
                        return f"node:{target}"
        return "board:working"
