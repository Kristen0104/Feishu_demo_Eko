from __future__ import annotations

from pathlib import Path

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import BoardChangeSchema
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
    FeishuBoardElementMappingSchema,
    FeishuBoardSourceSchema,
)


def test_canvas_repository_persists_working_board_and_history_to_disk(tmp_path: Path) -> None:
    storage_dir = tmp_path / "canvas-store"
    first_repo = CanvasRepository(storage_dir=storage_dir)

    updated_board = first_repo.apply_change(
        "session-persist-001",
        BoardChangeSchema(
            change_id="change-persist-001",
            session_id="session-persist-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-123",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "persisted"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "persisted"}]},
            },
            base_version="v1",
            result_version="v2",
        ),
    )

    assert updated_board.latest_version == 2
    assert updated_board.latest_snapshot["nodes"][0]["text"] == "persisted"

    second_repo = CanvasRepository(storage_dir=storage_dir)
    board = second_repo.get_working_board("session-persist-001")
    history = second_repo.list_recent_changes("session-persist-001")

    assert board.latest_version == 2
    assert board.latest_snapshot["nodes"][0]["text"] == "persisted"
    assert history[0].change_id == "change-persist-001"
    assert history[0].actor_id == "user-123"
    assert history[0].target_scope == "node:node-1"


def test_canvas_repository_updates_and_persists_element_mappings_from_change(
    tmp_path: Path,
) -> None:
    storage_dir = tmp_path / "canvas-store"
    repo = CanvasRepository(storage_dir=storage_dir)
    repo.ingest_feishu_board(
        "session-map-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="session-map-001",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-first",
                title="Imported board",
                nodes=[{"id": "node-1", "text": "Imported"}],
                edges=[],
            ),
        ),
    )

    repo.apply_change(
        "session-map-001",
        BoardChangeSchema(
            change_id="change-map-001",
            session_id="session-map-001",
            change_type="user_edit",
            actor_type="user",
            payload={
                "latest_snapshot": {
                    "nodes": [
                        {"id": "node-1", "text": "Imported"},
                        {"id": "node-2", "text": "New local node"},
                    ]
                },
                "crdt_document": {
                    "nodes": [
                        {"id": "node-1", "text": "Imported"},
                        {"id": "node-2", "text": "New local node"},
                    ]
                },
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "source_import",
                        "mapping_status": "conflicted",
                        "metadata": {"whiteboard_id": "wb-first"},
                    },
                    {
                        "source_element_id": "local-node-2",
                        "working_element_id": "node-2",
                        "element_type": "node",
                        "origin_type": "user",
                        "mapping_status": "active",
                        "metadata": {"created_from": "manual_edit"},
                    },
                ],
            },
            base_version="v1",
            result_version="v2",
        ),
    )

    detail = repo.get_session_detail("session-map-001")
    second_repo = CanvasRepository(storage_dir=storage_dir)
    persisted_detail = second_repo.get_session_detail("session-map-001")

    assert detail.element_mappings[0].mapping_status == "conflicted"
    assert detail.element_mappings[1].origin_type == "user"
    assert detail.element_mappings[1].metadata["created_from"] == "manual_edit"
    assert persisted_detail.element_mappings[0].mapping_status == "conflicted"
    assert persisted_detail.element_mappings[1].working_element_id == "node-2"


def test_canvas_repository_merges_element_mappings_by_working_element_id(
    tmp_path: Path,
) -> None:
    storage_dir = tmp_path / "canvas-store"
    repo = CanvasRepository(storage_dir=storage_dir)
    repo.ingest_feishu_board(
        "session-map-merge-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="session-map-merge-001",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-first",
                title="Imported board",
                nodes=[
                    {"id": "node-1", "text": "Imported"},
                    {"id": "node-2", "text": "Existing"},
                ],
                edges=[],
            ),
            element_mappings=[
                FeishuBoardElementMappingSchema(
                    source_element_id="node-1",
                    working_element_id="node-1",
                    element_type="node",
                    origin_type="source_import",
                    mapping_status="active",
                    metadata={"whiteboard_id": "wb-first"},
                ),
                FeishuBoardElementMappingSchema(
                    source_element_id="node-2",
                    working_element_id="node-2",
                    element_type="node",
                    origin_type="source_import",
                    mapping_status="active",
                    metadata={"whiteboard_id": "wb-first"},
                ),
            ],
        ),
    )

    repo.apply_change(
        "session-map-merge-001",
        BoardChangeSchema(
            change_id="change-map-merge-001",
            session_id="session-map-merge-001",
            change_type="user_edit",
            actor_type="user",
            payload={
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {
                            "whiteboard_id": "wb-first",
                            "updated_from": "manual_merge",
                        },
                    }
                ]
            },
            base_version="v1",
            result_version="v2",
        ),
    )

    persisted_detail = CanvasRepository(storage_dir=storage_dir).get_session_detail(
        "session-map-merge-001"
    )

    assert [mapping.working_element_id for mapping in persisted_detail.element_mappings] == [
        "node-1",
        "node-2",
    ]
    assert persisted_detail.element_mappings[0].mapping_status == "conflicted"
    assert persisted_detail.element_mappings[0].origin_type == "merge"
    assert (
        persisted_detail.element_mappings[0].metadata["updated_from"]
        == "manual_merge"
    )
    assert persisted_detail.element_mappings[1].mapping_status == "active"
    assert persisted_detail.element_mappings[1].source_element_id == "node-2"


def test_canvas_repository_reimport_updates_source_and_records_conflict_without_overwriting_working_copy(
    tmp_path: Path,
) -> None:
    storage_dir = tmp_path / "canvas-store"
    repo = CanvasRepository(storage_dir=storage_dir)
    repo.ingest_feishu_board(
        "session-reimport-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="session-reimport-001",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-first",
                title="Imported board v1",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
                metadata={"source_version": "v1"},
            ),
            element_mappings=[
                FeishuBoardElementMappingSchema(
                    source_element_id="node-1",
                    working_element_id="node-1",
                    element_type="node",
                    origin_type="source_import",
                    mapping_status="active",
                    metadata={"source_version": "v1"},
                )
            ],
        ),
    )
    repo.apply_change(
        "session-reimport-001",
        BoardChangeSchema(
            change_id="change-local-001",
            session_id="session-reimport-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Local edit"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Local edit"}]},
            },
            base_version="v1",
            result_version="v2",
        ),
    )

    detail = repo.ingest_feishu_board(
        "session-reimport-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="session-reimport-001",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-first",
                title="Imported board v2",
                nodes=[{"id": "node-1", "text": "Source changed"}],
                edges=[],
                metadata={"source_version": "v2"},
            ),
            element_mappings=[
                FeishuBoardElementMappingSchema(
                    source_element_id="node-1",
                    working_element_id="node-1",
                    element_type="node",
                    origin_type="source_import",
                    mapping_status="active",
                    metadata={"source_version": "v2"},
                )
            ],
        ),
    )

    assert detail.source_board.source_version == "v2"
    assert detail.source_board.raw_payload["source_board"]["title"] == "Imported board v2"
    assert detail.working_board.latest_snapshot["nodes"][0]["text"] == "Local edit"
    assert detail.element_mappings[0].mapping_status == "conflicted"
    assert detail.element_mappings[0].metadata["conflict_reason"] == "source_version_changed"
    assert detail.recent_changes[-1].change_type == "conflict_detected"
    assert detail.recent_changes[-1].actor_type == "feishu"
    assert detail.recent_changes[-1].target_scope == "board:wb-first"
