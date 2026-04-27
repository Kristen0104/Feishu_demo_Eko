from __future__ import annotations

from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container
from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import (
    BoardChangeSchema,
    BoardPatchSchema,
    BoardSessionSchema,
    CanvasGenerationRequestSchema,
    EkoWorkingBoardSchema,
    FeishuSourceBoardSchema,
)
from app.modules.canvas.service import CanvasService
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.service import FeishuService
from app.modules.feishu.schemas import FeishuBoardAdapterPayloadSchema, FeishuBoardSourceSchema
from tests.modules.test_feishu_document_contract import DummyHttpClient, DummyResponse


class StubCanvasAiService:
    def generate_patch(
        self,
        *,
        session_id: str,
        payload: CanvasGenerationRequestSchema,
    ) -> BoardPatchSchema:
        return BoardPatchSchema(
            generation_mode=payload.generation_mode,
            patch_id=f"{session_id}-patch-001",
            summary="stub generated board",
            operations=[],
            full_board={
                "nodes": [
                    {"id": "generated-start", "type": "topic", "text": "开始"},
                    {"id": "generated-plan", "type": "note", "text": "推进计划"},
                    {"id": "generated-end", "type": "topic", "text": "结束"},
                ],
                "edges": [
                    {"id": "edge-1", "from": "generated-start", "to": "generated-plan"},
                    {"id": "edge-2", "from": "generated-plan", "to": "generated-end"},
                ],
                "viewport": {"x": 0, "y": 0, "zoom": 1},
            },
            targeted_patch=None,
        )


def _build_client(
    canvas_service: CanvasService | None = None,
    feishu_service: FeishuService | None = None,
) -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    if canvas_service is not None:
        app.dependency_overrides[get_canvas_service] = lambda: canvas_service
    if feishu_service is not None:
        app.dependency_overrides[get_feishu_service] = lambda: feishu_service
    return TestClient(app)


class MermaidImportHttpClient(DummyHttpClient):
    def __init__(self) -> None:
        super().__init__()
        self.syntax_import_payloads: list[dict[str, object]] = []
        self.syntax_imported = False

    def post(
        self,
        url: str,
        json: dict[str, object],
        timeout: int,
        headers: dict[str, str] | None = None,
    ) -> DummyResponse:
        self.calls.append(("POST", url))
        if url.endswith("/nodes/plantuml"):
            self.syntax_imported = True
            self.syntax_import_payloads.append(json)
            return DummyResponse(200, {"code": 0, "data": {"node_ids": ["mermaid-1"]}})
        return super().post(url, json, timeout, headers)

    def get(self, url: str, headers: dict[str, str], timeout: int) -> DummyResponse:
        parsed = urlparse(url)
        if parsed.path.endswith("/nodes") and self.syntax_imported:
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "node_id": "mermaid-start",
                                "title": "Start",
                                "type": "text_shape",
                                "x": 120,
                                "y": 160,
                                "width": 240,
                                "height": 64,
                            },
                            {
                                "node_id": "mermaid-end",
                                "title": "Review",
                                "type": "text_shape",
                                "x": 420,
                                "y": 160,
                                "width": 260,
                                "height": 64,
                            },
                        ],
                    },
                },
            )
        return super().get(url, headers, timeout)


def test_canvas_board_schemas_support_collaboration_and_offline_fields() -> None:
    board_session = BoardSessionSchema(
        session_id="canvas-demo-001",
        title="Weekly planning canvas",
        owner_user_id="user-1",
        collaborator_ids=["user-2"],
        permission_mode="collaborative",
        sync_state="idle",
        offline_capability="single_user_only",
    )

    feishu_source = FeishuSourceBoardSchema(
        source_board_id="source-1",
        session_id="canvas-demo-001",
        source_version="v1",
        raw_payload={"nodes": []},
    )

    working_board = EkoWorkingBoardSchema(
        working_board_id="working-1",
        session_id="canvas-demo-001",
        latest_version=3,
        crdt_document={"nodes": []},
        latest_snapshot={"nodes": []},
        offline_state="dirty",
    )

    recent_change = BoardChangeSchema(
        change_id="change-1",
        session_id="canvas-demo-001",
        change_type="offline_replay",
        actor_type="system",
        actor_id="system-replayer",
        target_scope="working_board",
        payload={"replayedChangeIds": ["change-0"]},
        base_version="v2",
        result_version="v3",
    )

    assert board_session.collaborator_ids == ["user-2"]
    assert board_session.offline_capability == "single_user_only"
    assert feishu_source.source_board_id == "source-1"
    assert working_board.latest_version == 3
    assert working_board.offline_state == "dirty"
    assert recent_change.change_type == "offline_replay"
    assert recent_change.actor_id == "system-replayer"
    assert recent_change.target_scope == "working_board"


def test_canvas_session_route_keeps_stub_contract() -> None:
    client = _build_client()

    response = client.get("/api/v1/canvas/sessions/session-123")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "success",
        "data": {
            "session_id": "session-123",
            "title": "Stub Canvas Session",
            "mode": "canvas",
        },
    }


def test_canvas_state_route_returns_collaboration_and_offline_contract() -> None:
    client = _build_client()

    response = client.get("/api/v1/canvas/sessions/session-123/state")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "success",
        "data": {
            "session_id": "session-123",
            "title": "Stub Canvas Session",
            "mode": "canvas",
            "owner_user_id": "creator-001",
            "collaborator_ids": ["editor-002", "reviewer-003"],
            "permission_mode": "collaborative",
            "sync_state": "idle",
            "offline_capability": "single_user_only",
        },
    }


def test_canvas_session_detail_route_returns_default_detail_contract() -> None:
    client = _build_client()

    response = client.get("/api/v1/canvas/sessions/session-123/detail")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["session"]["session_id"] == "session-123"
    assert payload["session"]["permission_mode"] == "collaborative"
    assert payload["source_board"]["source_board_id"] == "session-123-source"
    assert payload["working_board"]["latest_version"] == 1
    assert payload["working_board"]["offline_state"] == "clean"
    assert payload["element_mappings"] == []
    assert payload["recent_changes"] == []


def test_canvas_source_board_route_returns_default_contract() -> None:
    client = _build_client()

    response = client.get("/api/v1/canvas/sessions/session-123/source-board")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "success",
        "data": {
            "source_board_id": "session-123-source",
            "session_id": "session-123",
            "source_version": "v10",
            "raw_payload": {
                "nodes": [{"id": "source-node-1", "text": "Imported idea"}],
                "edges": [],
            },
            "sync_cursor": "cursor-session-123",
        },
    }


def test_canvas_mappings_route_returns_default_contract() -> None:
    client = _build_client()

    response = client.get("/api/v1/canvas/sessions/session-123/mappings")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "success",
        "data": [],
    }


def test_canvas_can_import_feishu_document_whiteboard_into_session_detail(
    tmp_path,
) -> None:
    from tests.modules.test_feishu_document_contract import DummyHttpClient

    client = _build_client(
        canvas_service=CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas")),
        feishu_service=FeishuService(
            client=FeishuClient(
                http_client=DummyHttpClient(),
                access_token_provider=lambda: "tenant-token-001",
            )
        ),
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-from-doc-001/import-feishu-document",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["session"]["session_id"] == "canvas-from-doc-001"
    assert payload["source_board"]["source_board_id"] == "wb-first"
    assert payload["source_board"]["source_version"] == (
        "feishu-doc-blocks:QFQVd8EEnoD58zxNwLNcmJRJnAg:block-2:wb-first"
    )
    assert payload["source_board"]["raw_payload"]["source_metadata"]["share_url"] == (
        "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink"
    )
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["id"] == "node-1"
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "Start"
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["type"] == "text_shape"
    assert payload["working_board"]["latest_snapshot"]["nodes"][1]["id"] == "node-2"
    assert payload["working_board"]["latest_snapshot"]["nodes"][1]["text"] == "Discuss"
    assert payload["element_mappings"][0]["source_element_id"] == "node-1"
    assert payload["element_mappings"][0]["working_element_id"] == "node-1"
    assert payload["element_mappings"][0]["origin_type"] == "source_import"
    assert payload["recent_changes"][0]["change_type"] == "source_import"
    assert payload["recent_changes"][0]["actor_id"] == "wb-first"
    assert payload["recent_changes"][0]["target_scope"] == "board:wb-first"
    assert payload["recent_changes"][0]["payload"]["element_mappings"][0]["origin_type"] == (
        "source_import"
    )
    assert (
        payload["recent_changes"][0]["payload"]["element_mappings"][0]["metadata"][
            "whiteboard_id"
        ]
        == "wb-first"
    )


def test_canvas_can_import_mermaid_into_existing_session_and_refresh_working_board(
    tmp_path,
) -> None:
    http_client = MermaidImportHttpClient()
    client = _build_client(
        canvas_service=CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas")),
        feishu_service=FeishuService(
            client=FeishuClient(
                http_client=http_client,
                access_token_provider=lambda: "tenant-token-001",
            )
        ),
    )

    import_response = client.post(
        "/api/v1/canvas/sessions/canvas-mermaid-001/import-feishu-document",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
        },
    )
    assert import_response.status_code == 200

    response = client.post(
        "/api/v1/canvas/sessions/canvas-mermaid-001/import-mermaid",
        json={
            "code": "graph TD; A-->B;",
            "style_type": 1,
            "diagram_type": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["detail"]["source_board"]["source_board_id"] == "wb-first"
    assert (
        payload["detail"]["working_board"]["latest_snapshot"]["nodes"][0]["id"]
        == "mermaid-start"
    )
    assert (
        payload["detail"]["working_board"]["latest_snapshot"]["nodes"][0]["text"]
        == "Start"
    )
    assert (
        payload["detail"]["working_board"]["latest_snapshot"]["nodes"][1]["id"]
        == "mermaid-end"
    )
    assert (
        payload["detail"]["working_board"]["latest_snapshot"]["nodes"][1]["text"]
        == "Review"
    )
    assert http_client.syntax_imported is True
    assert http_client.syntax_import_payloads[-1] == {
        "plant_uml_code": "graph TD; A-->B;",
        "style_type": 1,
        "syntax_type": 2,
        "diagram_type": 0,
    }


def test_canvas_source_board_and_mappings_routes_expose_imported_session_state(
    tmp_path,
) -> None:
    from tests.modules.test_feishu_document_contract import DummyHttpClient

    client = _build_client(
        canvas_service=CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas")),
        feishu_service=FeishuService(
            client=FeishuClient(
                http_client=DummyHttpClient(),
                access_token_provider=lambda: "tenant-token-001",
            )
        ),
    )

    client.post(
        "/api/v1/canvas/sessions/canvas-from-doc-001/import-feishu-document",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
        },
    )

    source_board_response = client.get(
        "/api/v1/canvas/sessions/canvas-from-doc-001/source-board"
    )
    mappings_response = client.get(
        "/api/v1/canvas/sessions/canvas-from-doc-001/mappings"
    )

    assert source_board_response.status_code == 200
    assert source_board_response.json()["data"]["source_board_id"] == "wb-first"
    assert source_board_response.json()["data"]["source_version"] == (
        "feishu-doc-blocks:QFQVd8EEnoD58zxNwLNcmJRJnAg:block-2:wb-first"
    )
    assert source_board_response.json()["data"]["raw_payload"]["source_metadata"][
        "share_url"
    ] == (
        "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink"
    )

    assert mappings_response.status_code == 200
    assert mappings_response.json()["data"][0]["source_element_id"] == "node-1"
    assert mappings_response.json()["data"][0]["working_element_id"] == "node-1"
    assert mappings_response.json()["data"][0]["origin_type"] == "source_import"
    assert mappings_response.json()["data"][0]["metadata"]["whiteboard_id"] == "wb-first"


def test_canvas_refresh_feishu_document_route_returns_detail_for_same_source_version(
    tmp_path,
) -> None:
    class StubFeishuService:
        def __init__(self) -> None:
            self.calls = 0

        def resolve_document_whiteboard_import_payload(
            self,
            *,
            share_url: str,
            session_id: str,
        ) -> FeishuBoardAdapterPayloadSchema:
            self.calls += 1
            return FeishuBoardAdapterPayloadSchema(
                session_id=session_id,
                source_board=FeishuBoardSourceSchema(
                    board_id="wb-refresh",
                    title="Refresh board",
                    nodes=[{"id": "node-1", "text": "Original"}],
                    edges=[],
                    metadata={"source_version": "v1", "share_url": share_url},
                ),
            )

    feishu_service = StubFeishuService()
    client = _build_client(
        canvas_service=CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas")),
        feishu_service=feishu_service,  # type: ignore[arg-type]
    )

    first = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-001/import-feishu-document",
        json={"share_url": "https://example.feishu.cn/docx/doc-001"},
    )
    second = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-001/refresh-feishu-document",
        json={"share_url": "https://example.feishu.cn/docx/doc-001"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    payload = second.json()["data"]
    assert payload["session"]["session_id"] == "canvas-refresh-001"
    assert payload["session"]["permission_mode"] == "collaborative"
    assert payload["source_board"]["source_board_id"] == "wb-refresh"
    assert payload["source_board"]["source_version"] == "v1"
    assert payload["working_board"]["working_board_id"] == "wb-refresh-working"
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "Original"
    assert payload["session"]["sync_state"] == "idle"
    assert payload["element_mappings"][0]["source_element_id"] == "node-1"
    assert payload["element_mappings"][0]["working_element_id"] == "node-1"
    assert payload["element_mappings"][0]["metadata"]["inferred"] is True
    assert payload["recent_changes"][-1]["change_type"] == "source_import"


def test_canvas_refresh_feishu_document_route_surfaces_conflict_on_source_change(
    tmp_path,
) -> None:
    class StubFeishuService:
        def __init__(self) -> None:
            self.calls = 0

        def resolve_document_whiteboard_import_payload(
            self,
            *,
            share_url: str,
            session_id: str,
        ) -> FeishuBoardAdapterPayloadSchema:
            self.calls += 1
            version = "v1" if self.calls == 1 else "v2"
            title = "Refresh board v1" if self.calls == 1 else "Refresh board v2"
            text = "Original" if self.calls == 1 else "Source changed"
            return FeishuBoardAdapterPayloadSchema(
                session_id=session_id,
                source_board=FeishuBoardSourceSchema(
                    board_id="wb-refresh-change",
                    title=title,
                    nodes=[{"id": "node-1", "text": text}],
                    edges=[],
                    metadata={"source_version": version, "share_url": share_url},
                ),
            )

    feishu_service = StubFeishuService()
    canvas_service = CanvasService(
        repository=CanvasRepository(storage_dir=tmp_path / "canvas"),
        ai_service=StubCanvasAiService(),
    )
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=feishu_service,  # type: ignore[arg-type]
    )

    client.post(
        "/api/v1/canvas/sessions/canvas-refresh-002/import-feishu-document",
        json={"share_url": "https://example.feishu.cn/docx/doc-002"},
    )
    canvas_service.apply_change(
        "canvas-refresh-002",
        BoardChangeSchema(
            change_id="change-local-refresh-001",
            session_id="canvas-refresh-002",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-refresh-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Local edit"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Local edit"}]},
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    response = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-002/refresh-feishu-document",
        json={"share_url": "https://example.feishu.cn/docx/doc-002"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["session"]["session_id"] == "canvas-refresh-002"
    assert payload["source_board"]["source_version"] == "v2"
    assert payload["source_board"]["raw_payload"]["source_board"]["title"] == "Refresh board v2"
    assert payload["working_board"]["latest_version"] == 2
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "Local edit"
    assert payload["session"]["sync_state"] == "conflict"
    assert payload["element_mappings"][0]["mapping_status"] == "conflicted"
    assert payload["element_mappings"][0]["metadata"]["inferred"] is True
    assert (
        payload["element_mappings"][0]["metadata"]["conflict_reason"]
        == "source_version_changed"
    )
    assert [change["change_type"] for change in payload["recent_changes"]] == [
        "source_import",
        "user_edit",
        "conflict_detected",
    ]
    assert payload["recent_changes"][-1]["payload"] == {
        "reason": "source_version_changed",
        "previous_source_version": "v1",
        "incoming_source_version": "v2",
    }


def test_canvas_refresh_review_route_returns_detail_without_merge_review_when_source_stable(
    tmp_path,
) -> None:
    class StubFeishuService:
        def resolve_document_whiteboard_import_payload(
            self,
            *,
            share_url: str,
            session_id: str,
        ) -> FeishuBoardAdapterPayloadSchema:
            return FeishuBoardAdapterPayloadSchema(
                session_id=session_id,
                source_board=FeishuBoardSourceSchema(
                    board_id="wb-refresh-review-stable",
                    title="Stable board",
                    nodes=[{"id": "node-1", "text": "Original"}],
                    edges=[],
                    metadata={"source_version": "v1", "share_url": share_url},
                ),
            )

    client = _build_client(
        canvas_service=CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas")),
        feishu_service=StubFeishuService(),  # type: ignore[arg-type]
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-review-001/refresh-feishu-document-review",
        json={"share_url": "https://example.feishu.cn/docx/doc-review-001"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["detail"]["session"]["sync_state"] == "idle"
    assert payload["detail"]["source_board"]["source_version"] == "v1"
    assert payload["merge_review"] is None


def test_canvas_refresh_review_route_returns_auto_merge_review_on_source_conflict(
    tmp_path,
) -> None:
    class StubFeishuService:
        def __init__(self) -> None:
            self.calls = 0

        def resolve_document_whiteboard_import_payload(
            self,
            *,
            share_url: str,
            session_id: str,
        ) -> FeishuBoardAdapterPayloadSchema:
            self.calls += 1
            version = "v1" if self.calls == 1 else "v2"
            text = "Original" if self.calls == 1 else "Source changed"
            return FeishuBoardAdapterPayloadSchema(
                session_id=session_id,
                source_board=FeishuBoardSourceSchema(
                    board_id="wb-refresh-review-conflict",
                    title="Conflict board",
                    nodes=[{"id": "node-1", "text": text}],
                    edges=[],
                    metadata={"source_version": version, "share_url": share_url},
                ),
            )

    feishu_service = StubFeishuService()
    canvas_service = CanvasService(
        repository=CanvasRepository(storage_dir=tmp_path / "canvas"),
        ai_service=StubCanvasAiService(),
    )
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=feishu_service,  # type: ignore[arg-type]
    )

    client.post(
        "/api/v1/canvas/sessions/canvas-refresh-review-002/import-feishu-document",
        json={"share_url": "https://example.feishu.cn/docx/doc-review-002"},
    )
    canvas_service.apply_change(
        "canvas-refresh-review-002",
        BoardChangeSchema(
            change_id="change-refresh-review-001",
            session_id="canvas-refresh-review-002",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-review-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Local edit"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Local edit"}]},
            },
            base_version="v1",
            result_version="v2",
        ),
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-review-002/refresh-feishu-document-review",
        json={"share_url": "https://example.feishu.cn/docx/doc-review-002"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["detail"]["session"]["sync_state"] == "conflict"
    assert payload["detail"]["working_board"]["latest_snapshot"]["nodes"][0]["text"] == (
        "Local edit"
    )
    assert payload["merge_review"]["review_id"] == (
        "canvas-refresh-review-002-merge-review-001"
    )
    assert payload["merge_review"]["source_version"] == "v2"
    assert payload["merge_review"]["working_version"] == 2
    assert payload["merge_review"]["events"][0]["event_type"] == "create"
    assert payload["merge_review"]["events"][0]["reason"] == "initial_review_created"
    assert payload["merge_review"]["events"][0]["change_id"] == (
        "canvas-refresh-review-002-conflict-detected-2"
    )
    assert payload["merge_review"]["status"] == "pending_review"
    assert payload["merge_review"]["conflicts"][0]["element_id"] == "node-1"
    assert payload["merge_review"]["conflicts"][0]["mapping_status"] == "conflicted"
    assert payload["merge_review"]["conflicts"][0]["working_node"] == {
        "id": "node-1",
        "text": "Local edit",
    }
    assert payload["merge_review"]["conflicts"][0]["source_node"] == {
        "id": "node-1",
        "text": "Source changed",
    }


def test_canvas_refresh_review_route_reuses_open_review_and_rotates_after_resolution(
    tmp_path,
) -> None:
    class StubFeishuService:
        def __init__(self) -> None:
            self.calls = 0

        def resolve_document_whiteboard_import_payload(
            self,
            *,
            share_url: str,
            session_id: str,
        ) -> FeishuBoardAdapterPayloadSchema:
            self.calls += 1
            match self.calls:
                case 1:
                    version = "v1"
                    text = "Original"
                case 2:
                    version = "v2"
                    text = "Source changed once"
                case 3:
                    version = "v3"
                    text = "Source changed twice"
                case _:
                    version = "v4"
                    text = "Source changed three times"
            return FeishuBoardAdapterPayloadSchema(
                session_id=session_id,
                source_board=FeishuBoardSourceSchema(
                    board_id="wb-refresh-review-rotate",
                    title=f"Conflict board {version}",
                    nodes=[{"id": "node-1", "text": text}],
                    edges=[],
                    metadata={"source_version": version, "share_url": share_url},
                ),
            )

    feishu_service = StubFeishuService()
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=feishu_service,  # type: ignore[arg-type]
    )

    client.post(
        "/api/v1/canvas/sessions/canvas-refresh-review-003/import-feishu-document",
        json={"share_url": "https://example.feishu.cn/docx/doc-review-003"},
    )
    canvas_service.apply_change(
        "canvas-refresh-review-003",
        BoardChangeSchema(
            change_id="change-refresh-review-rotate-001",
            session_id="canvas-refresh-review-003",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-review-rotate-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Local edit"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Local edit"}]},
            },
            base_version="v1",
            result_version="v2",
        ),
    )

    first_conflict = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-review-003/refresh-feishu-document-review",
        json={"share_url": "https://example.feishu.cn/docx/doc-review-003"},
    )
    second_conflict = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-review-003/refresh-feishu-document-review",
        json={"share_url": "https://example.feishu.cn/docx/doc-review-003"},
    )

    assert first_conflict.status_code == 200
    assert second_conflict.status_code == 200
    assert first_conflict.json()["data"]["merge_review"]["review_id"] == (
        "canvas-refresh-review-003-merge-review-001"
    )
    assert second_conflict.json()["data"]["merge_review"]["review_id"] == (
        "canvas-refresh-review-003-merge-review-001"
    )
    assert second_conflict.json()["data"]["merge_review"]["source_version"] == "v3"
    assert len(second_conflict.json()["data"]["merge_review"]["events"]) == 2
    assert second_conflict.json()["data"]["merge_review"]["events"][1]["event_type"] == (
        "refresh"
    )
    assert second_conflict.json()["data"]["merge_review"]["events"][1]["reason"] == (
        "source_version_changed"
    )
    assert second_conflict.json()["data"]["merge_review"]["events"][1]["change_id"] == (
        "canvas-refresh-review-003-conflict-detected-2"
    )

    resolve_response = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-review-003/merge-resolve",
        json={
            "review_id": "canvas-refresh-review-003-merge-review-001",
            "actor_id": "reviewer-refresh-003",
            "resolutions": [
                {
                    "working_element_id": "node-1",
                    "resolution": "working",
                }
            ],
        },
    )
    assert resolve_response.status_code == 200

    canvas_service.apply_change(
        "canvas-refresh-review-003",
        BoardChangeSchema(
            change_id="change-refresh-review-rotate-002",
            session_id="canvas-refresh-review-003",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-review-rotate-002",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Local edit again"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Local edit again"}]},
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ],
            },
            base_version="v3",
            result_version="v4",
        ),
    )

    third_conflict = client.post(
        "/api/v1/canvas/sessions/canvas-refresh-review-003/refresh-feishu-document-review",
        json={"share_url": "https://example.feishu.cn/docx/doc-review-003"},
    )

    assert third_conflict.status_code == 200
    assert third_conflict.json()["data"]["merge_review"]["review_id"] == (
        "canvas-refresh-review-003-merge-review-002"
    )
    assert third_conflict.json()["data"]["merge_review"]["source_version"] == "v4"
    assert third_conflict.json()["data"]["merge_review"]["events"][0]["event_type"] == (
        "create"
    )
    assert third_conflict.json()["data"]["merge_review"]["events"][0]["reason"] == (
        "initial_review_created"
    )
    assert third_conflict.json()["data"]["merge_review"]["events"][0]["change_id"] == (
        "canvas-refresh-review-003-conflict-detected-4"
    )


def test_canvas_merge_reviews_route_lists_open_and_resolved_reviews_for_session(
    tmp_path,
) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=FeishuService(client=FeishuClient()),
    )

    canvas_service.ingest_feishu_board(
        "canvas-reviews-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-reviews-001",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-reviews-001",
                title="Review board",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-reviews-001",
        BoardChangeSchema(
            change_id="change-reviews-001",
            session_id="canvas-reviews-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-reviews-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Working text"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Working text"}]},
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ],
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    client.post(
        "/api/v1/canvas/sessions/canvas-reviews-001/merge-review",
        json={
            "source_version": "v12",
            "working_version": 2,
            "conflicts": [],
        },
    )
    client.post(
        "/api/v1/canvas/sessions/canvas-reviews-001/merge-resolve",
        json={
            "review_id": "canvas-reviews-001-merge-review-001",
            "actor_id": "reviewer-reviews-001",
            "resolutions": [
                {
                    "working_element_id": "node-1",
                    "resolution": "source",
                }
            ],
        },
    )
    canvas_service.apply_change(
        "canvas-reviews-001",
        BoardChangeSchema(
            change_id="change-reviews-002",
            session_id="canvas-reviews-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-reviews-002",
            target_scope="board:working",
            payload={
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ]
            },
            base_version="v3",
            result_version="v4",
        ),
    )
    client.post(
        "/api/v1/canvas/sessions/canvas-reviews-001/merge-review",
        json={
            "source_version": "v13",
            "working_version": 4,
            "conflicts": [],
        },
    )

    response = client.get("/api/v1/canvas/sessions/canvas-reviews-001/merge-reviews")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert [item["review_id"] for item in payload] == [
        "canvas-reviews-001-merge-review-001",
        "canvas-reviews-001-merge-review-002",
    ]
    assert [item["status"] for item in payload] == ["resolved", "pending_review"]
    assert payload[0]["summary"]["pending_conflicts"] == 0
    assert payload[1]["summary"]["pending_conflicts"] == 1


def test_canvas_export_feishu_board_route_returns_exported_payload_and_records_sync_export(
    tmp_path,
) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=FeishuService(client=FeishuClient()),
    )

    canvas_service.ingest_feishu_board(
        "canvas-export-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-export-001",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-export-001",
                title="Export board",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-export-001",
        BoardChangeSchema(
            change_id="change-export-001",
            session_id="canvas-export-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-export-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {
                    "nodes": [{"id": "node-1", "text": "Exported text"}],
                    "edges": [],
                },
                "crdt_document": {
                    "nodes": [{"id": "node-1", "text": "Exported text"}],
                    "edges": [],
                },
            },
            base_version="v1",
            result_version="v2",
        ),
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-export-001/export-feishu-board",
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["export_status"] == "exported"
    assert payload["exported_board"]["session_id"] == "canvas-export-001"
    assert payload["exported_board"]["source_board"]["nodes"][0]["text"] == "Exported text"
    assert payload["exported_board"]["working_board"]["latest_version"] == 2
    assert payload["detail"]["recent_changes"][-1]["change_type"] == "sync_export"
    assert payload["detail"]["recent_changes"][-1]["actor_id"] == "wb-export-001"
    assert payload["detail"]["recent_changes"][-1]["payload"]["exported_board"]["source_board"][
        "nodes"
    ][0]["text"] == "Exported text"
    assert payload["detail"]["source_board"]["raw_payload"]["last_export"]["source_board"][
        "nodes"
    ][0]["text"] == "Exported text"
    assert payload["detail"]["source_board"]["raw_payload"]["last_export_status"] == "exported"
    assert payload["detail"]["source_board"]["source_version"] == "canvas-sync:wb-export-001:v2"
    assert payload["detail"]["source_board"]["sync_cursor"] == "export:v2"
    assert payload["detail"]["session"]["sync_state"] == "idle"


def test_canvas_export_feishu_board_route_blocks_when_conflicts_exist_by_default(
    tmp_path,
) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=FeishuService(client=FeishuClient()),
    )

    canvas_service.ingest_feishu_board(
        "canvas-export-002",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-export-002",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-export-002",
                title="Conflict export board",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-export-002",
        BoardChangeSchema(
            change_id="change-export-conflict-001",
            session_id="canvas-export-002",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-export-conflict-001",
            target_scope="board:working",
            payload={
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ]
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    detail = canvas_service.get_session_detail("canvas-export-002")
    conflict_detail = detail.model_copy(
        update={
            "session": detail.session.model_copy(update={"sync_state": "conflict"})
        }
    )
    canvas_service._repository._write_detail(conflict_detail)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-export-002/export-feishu-board",
    )

    assert response.status_code == 409
    assert response.json()["detail"]["message"] == "Canvas session has unresolved conflicts"
    assert response.json()["detail"]["session_id"] == "canvas-export-002"


def test_canvas_export_feishu_board_route_can_force_export_with_conflicts(
    tmp_path,
) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=FeishuService(client=FeishuClient()),
    )

    canvas_service.ingest_feishu_board(
        "canvas-export-003",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-export-003",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-export-003",
                title="Conflict export board",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-export-003",
        BoardChangeSchema(
            change_id="change-export-conflict-002",
            session_id="canvas-export-003",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-export-conflict-002",
            target_scope="board:working",
            payload={
                "latest_snapshot": {
                    "nodes": [{"id": "node-1", "text": "Force exported"}],
                    "edges": [],
                },
                "crdt_document": {
                    "nodes": [{"id": "node-1", "text": "Force exported"}],
                    "edges": [],
                },
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ],
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    detail = canvas_service.get_session_detail("canvas-export-003")
    conflict_detail = detail.model_copy(
        update={
            "session": detail.session.model_copy(update={"sync_state": "conflict"})
        }
    )
    canvas_service._repository._write_detail(conflict_detail)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-export-003/export-feishu-board",
        json={"allow_conflicted_export": True},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["export_status"] == "exported_with_conflicts"
    assert payload["exported_board"]["source_board"]["nodes"][0]["text"] == "Force exported"
    assert payload["detail"]["recent_changes"][-1]["change_type"] == "sync_export"
    assert payload["detail"]["source_board"]["raw_payload"]["last_export_status"] == (
        "exported_with_conflicts"
    )
    assert payload["detail"]["source_board"]["source_version"] == "feishu-normalized"
    assert payload["detail"]["source_board"]["sync_cursor"] is None
    assert payload["detail"]["session"]["sync_state"] == "conflict"


def test_canvas_publish_feishu_board_route_returns_publish_result_and_stores_last_publish(
    tmp_path,
) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=FeishuService(client=FeishuClient()),
    )

    canvas_service.ingest_feishu_board(
        "canvas-publish-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-publish-001",
            source_board=FeishuBoardSourceSchema(
                board_id="wb-publish-001",
                title="Publish board",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-publish-001",
        BoardChangeSchema(
            change_id="change-publish-001",
            session_id="canvas-publish-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-publish-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {
                    "nodes": [{"id": "node-1", "text": "Published text"}],
                    "edges": [],
                },
                "crdt_document": {
                    "nodes": [{"id": "node-1", "text": "Published text"}],
                    "edges": [],
                },
            },
            base_version="v1",
            result_version="v2",
        ),
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-publish-001/publish-feishu-board",
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["export_status"] == "exported"
    assert payload["publish_result"]["mode"] == "adapter_only"
    assert payload["publish_result"]["accepted"] is True
    assert payload["publish_result"]["exported_board"]["source_board"]["nodes"][0]["text"] == (
        "Published text"
    )
    assert payload["detail"]["source_board"]["raw_payload"]["last_publish"]["mode"] == (
        "adapter_only"
    )


def test_canvas_single_user_flow_can_complete_import_generate_refresh_resolve_and_publish(
    tmp_path,
) -> None:
    class StatefulStubFeishuService:
        def __init__(self) -> None:
            self.calls = 0

        def resolve_document_whiteboard_import_payload(
            self,
            *,
            share_url: str,
            session_id: str,
        ) -> FeishuBoardAdapterPayloadSchema:
            self.calls += 1
            source_version = "v1" if self.calls == 1 else "v2"
            first_node_text = "Start" if self.calls == 1 else "Source changed"
            return FeishuBoardAdapterPayloadSchema(
                session_id=session_id,
                source_board=FeishuBoardSourceSchema(
                    board_id="wb-flow-001",
                    title="Flow board",
                    nodes=[
                        {
                            "id": "node-1",
                            "type": "text_shape",
                            "text": first_node_text,
                            "x": 120,
                            "y": 160,
                            "width": 240,
                            "height": 64,
                        },
                        {
                            "id": "node-2",
                            "type": "text_shape",
                            "text": "Discuss",
                            "x": 420,
                            "y": 160,
                            "width": 260,
                            "height": 64,
                        },
                    ],
                    edges=[],
                    metadata={
                        "source_version": source_version,
                        "share_url": share_url,
                        "document_id": "doc-flow-001",
                        "whiteboard_id": "wb-flow-001",
                    },
                ),
            )

        def export_board(
            self,
            payload: FeishuBoardAdapterPayloadSchema,
        ) -> FeishuBoardAdapterPayloadSchema:
            return FeishuService(client=FeishuClient()).export_board(payload)

        def publish_board(
            self,
            payload: FeishuBoardAdapterPayloadSchema,
        ):
            return FeishuService(client=FeishuClient()).publish_board(payload)

    canvas_service = CanvasService(
        repository=CanvasRepository(storage_dir=tmp_path / "canvas"),
        ai_service=StubCanvasAiService(),
    )
    feishu_service = StatefulStubFeishuService()
    client = _build_client(
        canvas_service=canvas_service,
        feishu_service=feishu_service,  # type: ignore[arg-type]
    )

    imported = client.post(
        "/api/v1/canvas/sessions/canvas-flow-001/import-feishu-document",
        json={"share_url": "https://example.feishu.cn/docx/doc-flow-001"},
    )
    assert imported.status_code == 200
    assert len(imported.json()["data"]["working_board"]["latest_snapshot"]["nodes"]) == 2

    generated = client.post(
        "/api/v1/canvas/sessions/canvas-flow-001/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成项目推进画板",
            "board_context": imported.json()["data"]["working_board"]["latest_snapshot"],
            "session_metadata": {},
            "selection_context": None,
        },
    )
    assert generated.status_code == 200
    assert len(generated.json()["data"]["full_board"]["nodes"]) >= 3

    applied = client.post(
        "/api/v1/canvas/sessions/canvas-flow-001/apply-patch",
        json=generated.json()["data"],
    )
    assert applied.status_code == 200
    assert applied.json()["data"]["working_board"]["latest_version"] == 2

    refreshed = client.post(
        "/api/v1/canvas/sessions/canvas-flow-001/refresh-feishu-document-review",
        json={"share_url": "https://example.feishu.cn/docx/doc-flow-001"},
    )
    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()["data"]
    assert refreshed_payload["detail"]["session"]["sync_state"] == "conflict"
    assert refreshed_payload["merge_review"]["summary"]["total_conflicts"] == 2

    resolved = client.post(
        "/api/v1/canvas/sessions/canvas-flow-001/merge-resolve",
        json={
            "review_id": refreshed_payload["merge_review"]["review_id"],
            "actor_id": "reviewer-flow-001",
            "resolutions": [
                {
                    "working_element_id": conflict["working_element_id"],
                    "resolution": "working",
                }
                for conflict in refreshed_payload["merge_review"]["conflicts"]
            ],
        },
    )
    assert resolved.status_code == 200
    resolved_payload = resolved.json()["data"]
    assert resolved_payload["session"]["sync_state"] == "idle"
    assert not any(
        mapping["mapping_status"] == "conflicted"
        for mapping in resolved_payload["element_mappings"]
    )

    exported = client.post(
        "/api/v1/canvas/sessions/canvas-flow-001/export-feishu-board",
    )
    assert exported.status_code == 200
    assert exported.json()["data"]["export_status"] == "exported"

    published = client.post(
        "/api/v1/canvas/sessions/canvas-flow-001/publish-feishu-board",
    )
    assert published.status_code == 200
    assert published.json()["data"]["publish_result"]["accepted"] is True
    assert published.json()["data"]["publish_result"]["mode"] == "adapter_only"
