from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.modules.canvas.schemas import (
    BoardChangeSchema,
    BoardSessionSchema,
    CanvasSessionDetailSchema,
    CanvasSessionSchema,
    EkoWorkingBoardSchema,
    FeishuSourceBoardSchema,
    MergeResolutionRequestSchema,
    MergeReviewRequestSchema,
    MergeReviewSchema,
)
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
    FeishuBoardElementMappingSchema,
    FeishuBoardPublishResultSchema,
    FeishuBoardSourceSchema,
    FeishuBoardWorkingSchema,
)


class CanvasRepository:
    def __init__(self, storage_dir: Path | str | None = None) -> None:
        if storage_dir is None:
            storage_dir = Path(tempfile.mkdtemp(prefix="eko_canvas_"))
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._working_boards: dict[str, EkoWorkingBoardSchema] = {}
        self._changes: dict[str, list[BoardChangeSchema]] = {}

    def _session_path(self, session_id: str) -> Path:
        return self._storage_dir / f"{session_id}.json"

    def _default_board_session(self, session_id: str) -> BoardSessionSchema:
        return BoardSessionSchema(
            session_id=session_id,
            title="Stub Canvas Session",
            owner_user_id="creator-001",
            collaborator_ids=["editor-002", "reviewer-003"],
            permission_mode="collaborative",
            sync_state="idle",
            offline_capability="single_user_only",
        )

    def _default_source_board(self, session_id: str) -> FeishuSourceBoardSchema:
        return FeishuSourceBoardSchema(
            source_board_id=f"{session_id}-source",
            session_id=session_id,
            source_version="v10",
            raw_payload={
                "nodes": [{"id": "source-node-1", "text": "Imported idea"}],
                "edges": [],
            },
            sync_cursor=f"cursor-{session_id}",
        )

    def _default_working_board(self, session_id: str) -> EkoWorkingBoardSchema:
        return EkoWorkingBoardSchema(
            working_board_id=f"{session_id}-working",
            session_id=session_id,
            latest_version=1,
            crdt_document={"nodes": [], "edges": []},
            latest_snapshot={"nodes": [], "edges": []},
            offline_state="clean",
        )

    def _default_detail(self, session_id: str) -> CanvasSessionDetailSchema:
        return CanvasSessionDetailSchema(
            session=self._default_board_session(session_id),
            source_board=self._default_source_board(session_id),
            working_board=self._default_working_board(session_id),
            element_mappings=[],
            recent_changes=[],
        )

    def _read_detail(self, session_id: str) -> CanvasSessionDetailSchema:
        path = self._session_path(session_id)
        if not path.exists():
            return self._default_detail(session_id)

        payload = json.loads(path.read_text(encoding="utf-8"))
        return CanvasSessionDetailSchema.model_validate(payload)

    def _write_detail(self, detail: CanvasSessionDetailSchema) -> None:
        path = self._session_path(detail.session.session_id)
        path.write_text(
            json.dumps(detail.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_session(self, session_id: str) -> CanvasSessionSchema:
        return CanvasSessionSchema(
            session_id=session_id,
            title="Stub Canvas Session",
        )

    def get_session_detail(self, session_id: str) -> CanvasSessionDetailSchema:
        return self._read_detail(session_id)

    def get_board_session(self, session_id: str) -> BoardSessionSchema:
        return self._read_detail(session_id).session

    def get_feishu_source_board(self, session_id: str) -> FeishuSourceBoardSchema:
        return self._read_detail(session_id).source_board

    def get_merge_review(self, session_id: str, review_id: str) -> MergeReviewSchema:
        detail = self._read_detail(session_id)
        for review in detail.merge_reviews:
            if review.review_id == review_id:
                return review
        raise KeyError(f"merge review not found: {review_id}")

    def list_merge_reviews(self, session_id: str) -> list[MergeReviewSchema]:
        return list(self._read_detail(session_id).merge_reviews)

    def _open_merge_review(
        self,
        detail: CanvasSessionDetailSchema,
    ) -> MergeReviewSchema | None:
        for review in reversed(detail.merge_reviews):
            if review.status != "resolved":
                return review
        return None

    def _next_merge_review_id(self, detail: CanvasSessionDetailSchema) -> str:
        return f"{detail.session.session_id}-merge-review-{len(detail.merge_reviews) + 1:03d}"

    def get_working_board(self, session_id: str) -> EkoWorkingBoardSchema:
        if session_id in self._working_boards:
            return self._working_boards[session_id]

        working_board = self._read_detail(session_id).working_board
        self._working_boards[session_id] = working_board
        return working_board

    def list_recent_changes(self, session_id: str) -> list[BoardChangeSchema]:
        if session_id in self._changes:
            return list(self._changes[session_id])
        return list(self._read_detail(session_id).recent_changes)

    def build_feishu_export_payload(
        self,
        session_id: str,
    ) -> FeishuBoardAdapterPayloadSchema:
        detail = self._read_detail(session_id)
        raw_source_board = detail.source_board.raw_payload.get("source_board", {})
        if not isinstance(raw_source_board, dict):
            raw_source_board = {}
        source_title = str(raw_source_board.get("title", "Canvas Export")).strip() or "Canvas Export"
        source_board = FeishuBoardSourceSchema(
            board_id=str(
                raw_source_board.get("board_id", detail.source_board.source_board_id)
            ).strip()
            or detail.source_board.source_board_id,
            title=source_title,
            nodes=list(detail.working_board.latest_snapshot.get("nodes", [])),
            edges=list(detail.working_board.latest_snapshot.get("edges", [])),
            metadata=(
                dict(raw_source_board.get("metadata", {}))
                if isinstance(raw_source_board.get("metadata"), dict)
                else {}
            ),
        )
        working_board = FeishuBoardWorkingSchema.model_validate(
            detail.working_board.model_dump(mode="json")
        )
        return FeishuBoardAdapterPayloadSchema(
            session_id=session_id,
            source_board=source_board,
            working_board=working_board,
            element_mappings=list(detail.element_mappings),
        )

    def record_sync_export(
        self,
        session_id: str,
        exported_board: FeishuBoardAdapterPayloadSchema,
        *,
        export_status: str,
    ) -> CanvasSessionDetailSchema:
        detail = self._read_detail(session_id)
        raw_payload = dict(detail.source_board.raw_payload)
        raw_payload["last_export"] = exported_board.model_dump(mode="json")
        raw_payload["last_export_status"] = export_status
        raw_payload["last_exported_version"] = detail.working_board.latest_version
        if export_status == "exported":
            next_source_version = (
                f"canvas-sync:{detail.source_board.source_board_id}:v"
                f"{detail.working_board.latest_version}"
            )
            next_sync_cursor = f"export:v{detail.working_board.latest_version}"
            raw_payload["last_synced_source_version"] = next_source_version
            raw_payload["last_sync_cursor"] = next_sync_cursor
        else:
            next_source_version = detail.source_board.source_version
            next_sync_cursor = detail.source_board.sync_cursor
        change_id = f"{session_id}-sync-export-{detail.working_board.latest_version}"
        updated_detail = detail.model_copy(
            update={
                "session": detail.session.model_copy(
                    update={
                        "sync_state": "idle"
                        if export_status == "exported"
                        else detail.session.sync_state
                    }
                ),
                "source_board": detail.source_board.model_copy(
                    update={
                        "source_version": next_source_version,
                        "sync_cursor": next_sync_cursor,
                        "raw_payload": raw_payload,
                    }
                ),
                "recent_changes": [
                    *detail.recent_changes,
                    BoardChangeSchema(
                        change_id=change_id,
                        session_id=session_id,
                        change_type="sync_export",
                        actor_type="system",
                        actor_id=detail.source_board.source_board_id,
                        target_scope=f"board:{detail.source_board.source_board_id}",
                        payload={
                            "export_status": export_status,
                            "exported_board": exported_board.model_dump(mode="json"),
                        },
                        base_version=f"v{detail.working_board.latest_version}",
                        result_version=f"v{detail.working_board.latest_version}",
                    ),
                ],
            }
        )
        self._write_detail(updated_detail)
        self._changes[session_id] = list(updated_detail.recent_changes)
        return updated_detail

    def record_publish_result(
        self,
        session_id: str,
        publish_result: FeishuBoardPublishResultSchema,
    ) -> CanvasSessionDetailSchema:
        detail = self._read_detail(session_id)
        raw_payload = dict(detail.source_board.raw_payload)
        raw_payload["last_publish"] = publish_result.model_dump(mode="json")
        updated_detail = detail.model_copy(
            update={
                "source_board": detail.source_board.model_copy(update={"raw_payload": raw_payload})
            }
        )
        self._write_detail(updated_detail)
        return updated_detail

    def ingest_feishu_board(
        self,
        session_id: str,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> CanvasSessionDetailSchema:
        detail = self._read_detail(session_id)
        source_metadata = dict(payload.source_board.metadata)
        incoming_source_version = str(
            source_metadata.get("source_version", "feishu-normalized")
        )
        has_existing_import = bool(
            detail.source_board.raw_payload.get("source_metadata")
            or detail.element_mappings
            or detail.recent_changes
        )
        source_version_changed = (
            has_existing_import
            and detail.source_board.source_version != incoming_source_version
        )
        source_board = FeishuSourceBoardSchema(
            source_board_id=payload.source_board.board_id,
            session_id=session_id,
            source_version=incoming_source_version,
            raw_payload={
                "source_metadata": source_metadata,
                "source_board": payload.source_board.model_dump(mode="json"),
                "adapter_payload": payload.model_dump(mode="json"),
            },
            sync_cursor=None,
        )
        working_board_payload = payload.working_board or {
            "working_board_id": f"{payload.source_board.board_id}-working",
            "session_id": session_id,
            "latest_version": 1,
            "crdt_document": {
                "nodes": list(payload.source_board.nodes),
                "edges": list(payload.source_board.edges),
            },
            "latest_snapshot": {
                "nodes": list(payload.source_board.nodes),
                "edges": list(payload.source_board.edges),
            },
            "offline_state": "clean",
        }
        if source_version_changed:
            working_board = detail.working_board
        else:
            if isinstance(working_board_payload, dict):
                working_board = EkoWorkingBoardSchema.model_validate(working_board_payload)
            else:
                working_board = EkoWorkingBoardSchema(
                    working_board_id=working_board_payload.working_board_id,
                    session_id=session_id,
                    latest_version=working_board_payload.latest_version,
                    crdt_document=working_board_payload.crdt_document,
                    latest_snapshot=working_board_payload.latest_snapshot,
                    offline_state=working_board_payload.offline_state,
                )

        updated_mappings = self._normalized_import_mappings(payload)
        updated_changes = [*detail.recent_changes]
        if source_version_changed:
            updated_mappings = self._mark_conflicted_source_mappings(
                detail.element_mappings
            )
            updated_changes.append(
                BoardChangeSchema(
                    change_id=f"{session_id}-conflict-detected-{working_board.latest_version}",
                    session_id=session_id,
                    change_type="conflict_detected",
                    actor_type="feishu",
                    actor_id=payload.source_board.board_id,
                    target_scope=f"board:{payload.source_board.board_id}",
                    payload={
                        "reason": "source_version_changed",
                        "previous_source_version": detail.source_board.source_version,
                        "incoming_source_version": incoming_source_version,
                    },
                    base_version=f"v{working_board.latest_version}",
                    result_version=f"v{working_board.latest_version}",
                )
            )
        else:
            updated_changes.append(
                BoardChangeSchema(
                    change_id=f"{session_id}-source-import-001",
                    session_id=session_id,
                    change_type="source_import",
                    actor_type="feishu",
                    actor_id=payload.source_board.board_id,
                    target_scope=f"board:{payload.source_board.board_id}",
                    payload=payload.model_dump(mode="json"),
                    base_version="v1",
                    result_version=f"v{working_board.latest_version}",
                )
            )
        updated_detail = detail.model_copy(
            update={
                "session": detail.session.model_copy(
                    update={
                        "sync_state": "conflict" if source_version_changed else "idle",
                    }
                ),
                "source_board": source_board,
                "working_board": working_board,
                "element_mappings": updated_mappings,
                "recent_changes": updated_changes,
            }
        )
        self._write_detail(updated_detail)
        self._working_boards[session_id] = working_board
        self._changes[session_id] = list(updated_detail.recent_changes)
        return updated_detail

    def _normalized_import_mappings(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> list[FeishuBoardElementMappingSchema]:
        if payload.element_mappings:
            return list(payload.element_mappings)

        inferred: list[FeishuBoardElementMappingSchema] = []
        source_metadata = dict(payload.source_board.metadata)
        for node in payload.source_board.nodes:
            node_id = str(node.get("id") or node.get("node_id") or "")
            if not node_id:
                continue
            inferred.append(
                FeishuBoardElementMappingSchema(
                    source_element_id=node_id,
                    working_element_id=node_id,
                    element_type="node",
                    origin_type="source_import",
                    mapping_status="active",
                    metadata={
                        "source_type": "feishu_document_whiteboard",
                        "document_id": source_metadata.get("document_id"),
                        "whiteboard_id": payload.source_board.board_id,
                        "block_id": source_metadata.get("block_id"),
                        "inferred": True,
                    },
                )
            )

        for edge in payload.source_board.edges:
            edge_id = str(edge.get("id") or edge.get("edge_id") or "")
            if not edge_id:
                continue
            inferred.append(
                FeishuBoardElementMappingSchema(
                    source_element_id=edge_id,
                    working_element_id=edge_id,
                    element_type="edge",
                    origin_type="source_import",
                    mapping_status="active",
                    metadata={
                        "source_type": "feishu_document_whiteboard",
                        "document_id": source_metadata.get("document_id"),
                        "whiteboard_id": payload.source_board.board_id,
                        "block_id": source_metadata.get("block_id"),
                        "inferred": True,
                    },
                )
            )

        return inferred

    def _mark_conflicted_source_mappings(
        self,
        existing_mappings: list[FeishuBoardElementMappingSchema],
    ) -> list[FeishuBoardElementMappingSchema]:
        updated: list[FeishuBoardElementMappingSchema] = []
        for mapping in existing_mappings:
            if mapping.origin_type in {"source_import", "merge"}:
                updated.append(
                    mapping.model_copy(
                        update={
                            "mapping_status": "conflicted",
                            "metadata": {
                                **mapping.metadata,
                                "conflict_reason": "source_version_changed",
                            },
                        }
                    )
                )
            else:
                updated.append(mapping)
        return updated

    def _merge_element_mappings(
        self,
        existing_mappings: list[FeishuBoardElementMappingSchema],
        payload_mappings: list[object],
    ) -> list[FeishuBoardElementMappingSchema]:
        merged_mappings = list(existing_mappings)
        index_by_working_element_id = {
            mapping.working_element_id: index
            for index, mapping in enumerate(merged_mappings)
        }

        for mapping_payload in payload_mappings:
            mapping = FeishuBoardElementMappingSchema.model_validate(mapping_payload)
            existing_index = index_by_working_element_id.get(mapping.working_element_id)
            if existing_index is None:
                index_by_working_element_id[mapping.working_element_id] = len(
                    merged_mappings
                )
                merged_mappings.append(mapping)
                continue
            merged_mappings[existing_index] = mapping

        return merged_mappings

    def apply_change(
        self,
        session_id: str,
        change: BoardChangeSchema,
    ) -> EkoWorkingBoardSchema:
        detail = self._read_detail(session_id)
        board = detail.working_board

        updated_board = board.model_copy(
            update={
                "latest_version": board.latest_version + 1,
                "latest_snapshot": change.payload.get(
                    "latest_snapshot",
                    board.latest_snapshot,
                ),
                "crdt_document": change.payload.get(
                    "crdt_document",
                    board.crdt_document,
                ),
                "offline_state": "dirty"
                if change.actor_type in {"user", "ai"}
                else board.offline_state,
            }
        )
        payload_mappings = change.payload.get("element_mappings")
        if isinstance(payload_mappings, list):
            updated_mappings = self._merge_element_mappings(
                existing_mappings=list(detail.element_mappings),
                payload_mappings=payload_mappings,
            )
        else:
            updated_mappings = list(detail.element_mappings)

        updated_detail = detail.model_copy(
            update={
                "working_board": updated_board,
                "element_mappings": updated_mappings,
                "recent_changes": [*detail.recent_changes, change],
            }
        )
        self._write_detail(updated_detail)
        self._working_boards[session_id] = updated_board
        self._changes[session_id] = list(updated_detail.recent_changes)
        return updated_board

    def build_merge_review(
        self,
        session_id: str,
        payload: MergeReviewRequestSchema,
    ) -> MergeReviewSchema:
        detail = self._read_detail(session_id)
        mapping_by_working_element_id = {
            mapping.working_element_id: mapping for mapping in detail.element_mappings
        }
        working_nodes = detail.working_board.latest_snapshot.get("nodes", [])
        if not isinstance(working_nodes, list):
            working_nodes = []
        working_node_by_id = {
            str(node.get("id", "")).strip(): node
            for node in working_nodes
            if isinstance(node, dict)
        }
        source_nodes = detail.source_board.raw_payload.get("source_board", {}).get("nodes", [])
        if not isinstance(source_nodes, list):
            source_nodes = []
        source_node_by_id = {
            str(node.get("id", "")).strip(): node
            for node in source_nodes
            if isinstance(node, dict)
        }
        raw_conflicts = payload.conflicts
        if not raw_conflicts:
            raw_conflicts = [
                {
                    "element_id": mapping.working_element_id,
                    "kind": str(mapping.metadata.get("kind", "mapping_conflict")),
                }
                for mapping in detail.element_mappings
                if mapping.mapping_status == "conflicted"
            ]
        conflicts: list[dict[str, object]] = []
        for conflict in raw_conflicts:
            if not isinstance(conflict, dict):
                continue
            merged_conflict = dict(conflict)
            element_id = str(conflict.get("element_id", "")).strip()
            mapping = mapping_by_working_element_id.get(element_id)
            if mapping is not None:
                working_node = working_node_by_id.get(mapping.working_element_id)
                source_node = source_node_by_id.get(mapping.source_element_id)
                merged_conflict.update(
                    {
                        "mapping_status": mapping.mapping_status,
                        "working_element_id": mapping.working_element_id,
                        "source_element_id": mapping.source_element_id,
                        "origin_type": mapping.origin_type,
                        "mapping_metadata": mapping.metadata,
                        "working_node": working_node,
                        "source_node": source_node,
                    }
                )
            merged_conflict["source_version"] = payload.source_version
            merged_conflict["working_version"] = payload.working_version
            conflicts.append(merged_conflict)
        existing_open_review = self._open_merge_review(detail)
        review = MergeReviewSchema(
            review_id=(
                existing_open_review.review_id
                if existing_open_review is not None
                else self._next_merge_review_id(detail)
            ),
            session_id=session_id,
            source_version=payload.source_version,
            working_version=payload.working_version,
            status="pending_review",
            summary=self._build_merge_review_summary(conflicts),
            conflicts=conflicts,
            events=[
                *(
                    list(existing_open_review.events)
                    if existing_open_review is not None
                    else []
                ),
                {
                    "event_type": "refresh"
                    if existing_open_review is not None
                    else "create",
                    "source_version": payload.source_version,
                    "working_version": payload.working_version,
                    "status": "pending_review",
                    "summary": self._build_merge_review_summary(conflicts),
                    "conflicts": json.loads(json.dumps(conflicts)),
                    "reason": (
                        "source_version_changed"
                        if existing_open_review is not None
                        else "initial_review_created"
                    ),
                    "change_id": self._latest_change_id(
                        detail,
                        "conflict_detected"
                        if (
                            existing_open_review is not None
                            or self._latest_change_id(detail, "conflict_detected")
                            is not None
                        )
                        else "source_import",
                    ),
                },
            ],
        )
        self._save_merge_review(session_id, review)
        return review

    def _build_merge_review_summary(
        self,
        conflicts: list[dict[str, object]],
    ) -> dict[str, int]:
        resolved_conflicts = sum(
            1 for conflict in conflicts if str(conflict.get("status", "")) == "resolved"
        )
        total_conflicts = len(conflicts)
        return {
            "total_conflicts": total_conflicts,
            "resolved_conflicts": resolved_conflicts,
            "pending_conflicts": max(total_conflicts - resolved_conflicts, 0),
        }

    def _save_merge_review(self, session_id: str, review: MergeReviewSchema) -> None:
        detail = self._read_detail(session_id)
        merge_reviews = list(detail.merge_reviews)
        for index, existing_review in enumerate(merge_reviews):
            if existing_review.review_id == review.review_id:
                merge_reviews[index] = review
                break
        else:
            merge_reviews.append(review)
        updated_detail = detail.model_copy(update={"merge_reviews": merge_reviews})
        self._write_detail(updated_detail)
        self._changes[session_id] = list(updated_detail.recent_changes)

    def _latest_change_id(
        self,
        detail: CanvasSessionDetailSchema,
        change_type: str,
    ) -> str | None:
        for change in reversed(detail.recent_changes):
            if change.change_type == change_type:
                return change.change_id
        return None

    def resolve_merge_review(
        self,
        session_id: str,
        payload: MergeResolutionRequestSchema,
    ) -> CanvasSessionDetailSchema:
        detail = self._read_detail(session_id)
        existing_review = None
        for review in detail.merge_reviews:
            if review.review_id == payload.review_id:
                existing_review = review
                break
        if existing_review is None:
            existing_review = self.build_merge_review(
                session_id,
                MergeReviewRequestSchema(
                    source_version=detail.source_board.source_version,
                    working_version=detail.working_board.latest_version,
                    conflicts=[],
                ),
            )
            if existing_review.review_id != payload.review_id:
                existing_review = existing_review.model_copy(
                    update={"review_id": payload.review_id}
                )
                self._save_merge_review(session_id, existing_review)
            detail = self._read_detail(session_id)
        snapshot = json.loads(json.dumps(detail.working_board.latest_snapshot))
        nodes = snapshot.get("nodes", [])
        if not isinstance(nodes, list):
            nodes = []
        node_index_by_id = {
            str(node.get("id", "")).strip(): index
            for index, node in enumerate(nodes)
            if isinstance(node, dict)
        }
        source_nodes = detail.source_board.raw_payload.get("source_board", {}).get("nodes", [])
        if not isinstance(source_nodes, list):
            source_nodes = []
        source_node_by_id = {
            str(node.get("id", "")).strip(): node
            for node in source_nodes
            if isinstance(node, dict)
        }
        updated_mappings: list[FeishuBoardElementMappingSchema] = []
        resolution_by_working_id = {
            item.working_element_id: item.resolution for item in payload.resolutions
        }
        resolved_items: list[dict[str, object]] = []
        for mapping in detail.element_mappings:
            resolution = resolution_by_working_id.get(mapping.working_element_id)
            if resolution is None:
                updated_mappings.append(mapping)
                continue
            if resolution == "source":
                source_node = source_node_by_id.get(mapping.source_element_id)
                node_index = node_index_by_id.get(mapping.working_element_id)
                if source_node is not None and node_index is not None:
                    nodes[node_index] = dict(source_node)
            updated_mappings.append(
                mapping.model_copy(
                    update={
                        "mapping_status": "active",
                        "origin_type": "merge",
                        "metadata": {
                            **mapping.metadata,
                            "resolved_by": resolution,
                            "review_id": payload.review_id,
                        },
                    }
                )
            )
            resolved_items.append(
                {
                    "working_element_id": mapping.working_element_id,
                    "source_element_id": mapping.source_element_id,
                    "resolution": resolution,
                }
            )
        snapshot["nodes"] = nodes
        updated_board = detail.working_board.model_copy(
            update={
                "latest_version": detail.working_board.latest_version + 1,
                "latest_snapshot": snapshot,
                "crdt_document": snapshot,
            }
        )
        remaining_conflicts = any(
            mapping.mapping_status == "conflicted" for mapping in updated_mappings
        )
        merge_resolved_change_id = (
            f"{session_id}-merge-resolved-{updated_board.latest_version}"
        )
        updated_reviews = list(detail.merge_reviews)
        if existing_review is not None:
            updated_conflicts: list[dict[str, object]] = []
            for conflict in existing_review.conflicts:
                if not isinstance(conflict, dict):
                    continue
                updated_conflict = dict(conflict)
                working_element_id = str(
                    updated_conflict.get("working_element_id")
                    or updated_conflict.get("element_id")
                    or ""
                ).strip()
                resolution = resolution_by_working_id.get(working_element_id)
                if resolution is not None:
                    updated_conflict["resolution"] = resolution
                    updated_conflict["status"] = "resolved"
                updated_conflicts.append(updated_conflict)
            updated_status = (
                "resolved"
                if updated_conflicts
                and all(
                    str(conflict.get("status", "")) == "resolved"
                    for conflict in updated_conflicts
                )
                else "partially_resolved"
            )
            updated_review = existing_review.model_copy(
                update={
                    "source_version": detail.source_board.source_version,
                    "working_version": updated_board.latest_version,
                    "status": updated_status,
                    "summary": self._build_merge_review_summary(updated_conflicts),
                    "conflicts": updated_conflicts,
                    "events": [
                        *existing_review.events,
                        {
                            "event_type": "resolve",
                            "source_version": detail.source_board.source_version,
                            "working_version": updated_board.latest_version,
                            "status": updated_status,
                            "summary": self._build_merge_review_summary(
                                updated_conflicts
                            ),
                            "conflicts": json.loads(json.dumps(updated_conflicts)),
                            "resolutions": resolved_items,
                            "actor_id": payload.actor_id or payload.review_id,
                            "change_id": merge_resolved_change_id,
                        },
                    ],
                }
            )
            updated_reviews = [
                updated_review if review.review_id == payload.review_id else review
                for review in updated_reviews
            ]
        updated_detail = detail.model_copy(
            update={
                "session": detail.session.model_copy(
                    update={"sync_state": "conflict" if remaining_conflicts else "idle"}
                ),
                "working_board": updated_board,
                "element_mappings": updated_mappings,
                "merge_reviews": updated_reviews,
                "recent_changes": [
                    *detail.recent_changes,
                    BoardChangeSchema(
                        change_id=merge_resolved_change_id,
                        session_id=session_id,
                        change_type="merge_resolved",
                        actor_type="system",
                        actor_id=payload.actor_id or payload.review_id,
                        target_scope="board:working",
                        payload={
                            "review_id": payload.review_id,
                            "resolutions": resolved_items,
                        },
                        base_version=f"v{detail.working_board.latest_version}",
                        result_version=f"v{updated_board.latest_version}",
                    ),
                ],
            }
        )
        self._write_detail(updated_detail)
        self._working_boards[session_id] = updated_board
        self._changes[session_id] = list(updated_detail.recent_changes)
        return updated_detail
