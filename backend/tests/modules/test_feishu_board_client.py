from __future__ import annotations

import json

import pytest

from app.config import Settings
from app.modules.feishu.board_client import FeishuBoardClient


def test_import_diagram_maps_cli_enums() -> None:
    client = FeishuBoardClient()

    result = client.import_diagram(
        "wbcn123",
        source="@startuml\nA->B\n@enduml",
        source_type="content",
        syntax="plantuml",
        diagram_type="flowchart",
        style="classic",
    )

    assert result["whiteboard_id"] == "wbcn123"
    assert result["ticket_id"] == "ticket-wbcn123"
    assert result["syntax_type"] == 1
    assert result["style_type"] == 2
    assert result["diagram_type_value"] == 6


def test_create_notes_uses_nodes_wrapper_and_returns_ids() -> None:
    client = FeishuBoardClient()

    result = client.create_notes(
        "wbcn123",
        nodes_json_or_nodes=[
            {"type": "composite_shape", "text": {"text": "A"}},
            {"type": "composite_shape", "text": {"text": "B"}},
        ],
        source_type="content",
        client_token="abc",
        user_id_type="open_id",
    )

    assert result["count"] == 2
    assert len(result["node_ids"]) == 2
    raw = client.get_board_nodes("wbcn123")
    assert raw["data"]["nodes"][result["node_ids"][0]]["type"] == "composite_shape"


def test_update_board_overwrite_dry_run_only_counts_existing_nodes() -> None:
    client = FeishuBoardClient()
    client.create_notes(
        "wbcn123",
        nodes_json_or_nodes=[{"type": "composite_shape", "text": {"text": "A"}}],
        source_type="content",
        client_token="",
        user_id_type="open_id",
    )

    result = client.update_board(
        "wbcn123",
        nodes_json_or_nodes=[{"type": "composite_shape", "text": {"text": "B"}}],
        overwrite=True,
        dry_run=True,
    )

    assert result["whiteboard_id"] == "wbcn123"
    assert result["dry_run"] is True
    assert result["existing_count"] == 1


def test_delete_board_nodes_removes_all_requested_ids() -> None:
    client = FeishuBoardClient()
    created = client.create_notes(
        "wbcn123",
        nodes_json_or_nodes=[
            {"type": "composite_shape", "text": {"text": "A"}},
            {"type": "composite_shape", "text": {"text": "B"}},
        ],
        source_type="content",
        client_token="",
        user_id_type="open_id",
    )

    result = client.delete_board_nodes("wbcn123", created["node_ids"])

    assert result["deleted_count"] == 2
    assert client.extract_board_node_ids("wbcn123") == []


def test_create_notes_sanitizes_cli_style_nodes_before_posting() -> None:
    client = FeishuBoardClient()

    result = client.create_notes(
        "wbcnSAN",
        nodes_json_or_nodes=[
            {
                "type": "composite_shape",
                "id": "readonly-id",
                "locked": True,
                "children": ["x"],
                "parent_id": "p1",
                "x": 100,
                "y": 120,
                "width": 180,
                "height": 55,
                "z_index": 10,
                "composite_shape": {"type": "round_rect", "unexpected": "drop"},
                "text": {
                    "text": "A",
                    "font_size": 14,
                    "text_color_type": 1,
                },
                "style": {
                    "fill_color": "#fff",
                    "fill_color_type": 1,
                    "border_color": "#000",
                    "border_color_type": 1,
                    "border_width": "medium",
                },
            },
            {
                "type": "connector",
                "width": 1,
                "height": 1,
                "z_index": 50,
                "connector": {
                    "shape": "polyline",
                    "start": {
                        "arrow_style": "none",
                        "attached_object": {
                            "id": "n1",
                            "position": {"x": 1, "y": 0.5},
                            "snap_to": "right",
                            "extra": "drop",
                        },
                    },
                    "end": {
                        "arrow_style": "triangle_arrow",
                        "attached_object": {
                            "id": "n2",
                            "position": {"x": 0, "y": 0.5},
                            "snap_to": "left",
                        },
                    },
                    "start_object": {"id": "readonly"},
                },
                "style": {
                    "border_color": "#BBBFC4",
                    "border_width": "narrow",
                    "fill_color": "#fff",
                },
            },
        ],
        source_type="content",
        client_token="",
        user_id_type="open_id",
    )

    raw = client.get_board_nodes("wbcnSAN")["data"]["nodes"]
    shape = raw[result["node_ids"][0]]
    connector = raw[result["node_ids"][1]]

    assert "id" in shape
    assert "locked" not in shape
    assert "children" not in shape
    assert "parent_id" not in shape
    assert shape["composite_shape"] == {"type": "round_rect"}
    assert shape["text"] == {
        "text": "A",
        "font_size": 14,
    }
    assert shape["style"] == {
        "fill_color": "#fff",
        "border_color": "#000",
        "border_width": "medium",
    }
    assert "start_object" not in connector["connector"]
    assert connector["connector"]["start"]["attached_object"] == {
        "id": "n1",
        "position": {"x": 1, "y": 0.5},
        "snap_to": "right",
    }
    assert connector["style"] == {
        "border_color": "#BBBFC4",
        "border_width": "narrow",
    }


def test_import_diagram_file_mode_requires_real_path(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = FeishuBoardClient()
    source_file = tmp_path / "diagram.mmd"
    source_file.write_text("flowchart TD\nA-->B", encoding="utf-8")

    result = client.import_diagram(
        "wbcnFILE",
        source=str(source_file),
        source_type="file",
        syntax="mermaid",
        diagram_type="flowchart",
        style="board",
    )

    assert result["whiteboard_id"] == "wbcnFILE"


def test_import_diagram_file_mode_raises_when_path_missing() -> None:
    client = FeishuBoardClient()

    with pytest.raises(FileNotFoundError, match="source file not found"):
        client.import_diagram(
            "wbcnMISS",
            source="/tmp/not-found-diagram.mmd",
            source_type="file",
            syntax="mermaid",
            diagram_type="flowchart",
            style="board",
        )


def test_resolve_whiteboard_id_from_document_returns_stub_without_credentials() -> None:
    client = FeishuBoardClient()

    resolved = client.resolve_whiteboard_id_from_document("AbCdEfGhIjKl")

    assert resolved == "resolved-from-AbCdEfGhIjKl"


def test_resolve_whiteboard_id_from_document_reads_docx_blocks_with_credentials() -> None:
    class DummyResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.status_code = 200
            self._payload = payload
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            self.calls.append(url)
            if url.endswith("/blocks/doccn123/children?page_size=500&document_revision_id=-1"):
                return DummyResponse(
                    {
                        "code": 0,
                        "data": {
                            "items": [{"block_type": 2}, {"block_type": 43, "board": {"token": "wbcnDOC"}}],
                            "has_more": False,
                        },
                    }
                )
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                {
                    "code": 0,
                    "tenant_access_token": "tenant-token",
                    "expire": 7200,
                }
            )

    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=DummyHttpClient(),  # type: ignore[arg-type]
    )

    resolved = client.resolve_whiteboard_id_from_document("doccn123")

    assert resolved == "wbcnDOC"


def test_resolve_whiteboard_id_from_document_ignores_non_board_blocks_and_paginates() -> None:
    class DummyResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.status_code = 200
            self._payload = payload
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if url.endswith("/blocks/doccn456/children?page_size=500&document_revision_id=-1"):
                return DummyResponse(
                    {
                        "code": 0,
                        "data": {
                            "items": [{"block_type": 2, "board": {"token": "ignore-me"}}],
                            "has_more": True,
                            "page_token": "next-page",
                        },
                    }
                )
            if url.endswith("/blocks/doccn456/children?page_size=500&document_revision_id=-1&page_token=next-page"):
                return DummyResponse(
                    {
                        "code": 0,
                        "data": {
                            "items": [{"block_type": 43, "board": {"token": "wbcnPAGE2"}}],
                            "has_more": False,
                        },
                    }
                )
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                {
                    "code": 0,
                    "tenant_access_token": "tenant-token",
                    "expire": 7200,
                }
            )

    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=DummyHttpClient(),  # type: ignore[arg-type]
    )

    resolved = client.resolve_whiteboard_id_from_document("doccn456")

    assert resolved == "wbcnPAGE2"


def test_resolve_whiteboard_id_from_document_falls_back_to_full_block_scan() -> None:
    class DummyResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.status_code = 200
            self._payload = payload
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if url.endswith("/blocks/doccn789/children?page_size=500&document_revision_id=-1"):
                return DummyResponse(
                    {
                        "code": 0,
                        "data": {
                            "items": [],
                            "has_more": False,
                        },
                    }
                )
            if url.endswith("/blocks?page_size=500"):
                return DummyResponse(
                    {
                        "code": 0,
                        "data": {
                            "items": [{"block_type": 43, "board": {"token": "wbcnFALLBACK"}}],
                            "has_more": False,
                        },
                    }
                )
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                {
                    "code": 0,
                    "tenant_access_token": "tenant-token",
                    "expire": 7200,
                }
            )

    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=DummyHttpClient(),  # type: ignore[arg-type]
    )

    resolved = client.resolve_whiteboard_id_from_document("doccn789")

    assert resolved == "wbcnFALLBACK"


def test_import_diagram_retries_rate_limit_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.feishu.board_client.time.sleep", lambda _: None)
    monkeypatch.setattr("app.modules.feishu.board_client.random.random", lambda: 0.0)

    class DummyResponse:
        def __init__(
            self,
            *,
            status_code: int,
            payload: dict[str, object],
            headers: dict[str, str] | None = None,
        ) -> None:
            self.status_code = status_code
            self._payload = payload
            self.headers = headers or {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def __init__(self) -> None:
            self.import_calls = 0

        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if "/nodes/plantuml" in url:
                self.import_calls += 1
                if self.import_calls <= 2:
                    return DummyResponse(
                        status_code=429,
                        payload={"code": 99991400, "msg": "frequency limit"},
                        headers={"x-ogw-ratelimit-reset": "0.0"},
                    )
                return DummyResponse(
                    status_code=200,
                    payload={"code": 0, "data": {"ticket_id": "ticket-success"}},
                )
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                status_code=200,
                payload={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
            )

    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=DummyHttpClient(),  # type: ignore[arg-type]
    )

    result = client.import_diagram(
        "wbcnRETRY",
        source="flowchart TD\nA-->B",
        source_type="content",
        syntax="mermaid",
        diagram_type="flowchart",
        style="board",
    )

    assert result["ticket_id"] == "ticket-success"


def test_import_diagram_does_not_retry_permanent_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.feishu.board_client.time.sleep", lambda _: None)

    class DummyResponse:
        def __init__(self, *, status_code: int, payload: dict[str, object]) -> None:
            self.status_code = status_code
            self._payload = payload
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def __init__(self) -> None:
            self.import_calls = 0

        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if "/nodes/plantuml" in url:
                self.import_calls += 1
                return DummyResponse(
                    status_code=200,
                    payload={"code": 40001, "msg": "Parse error: invalid syntax"},
                )
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                status_code=200,
                payload={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
            )

    http_client = DummyHttpClient()
    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=http_client,  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="Parse error"):
        client.import_diagram(
            "wbcnFAIL",
            source="@startuml\nA->B\n@enduml",
            source_type="content",
            syntax="plantuml",
            diagram_type="auto",
            style="board",
        )

    assert http_client.import_calls == 1


def test_create_notes_raises_when_credentials_exist_and_request_fails() -> None:
    class DummyResponse:
        def __init__(self, *, status_code: int, payload: dict[str, object]) -> None:
            self.status_code = status_code
            self._payload = payload
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if "/nodes?user_id_type=open_id" in url:
                return DummyResponse(
                    status_code=500,
                    payload={"code": 50001, "msg": "internal error"},
                )
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                status_code=200,
                payload={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
            )

    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=DummyHttpClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="HTTP 500"):
        client.create_notes(
            "wbcnERR",
            nodes_json_or_nodes=[{"type": "composite_shape", "text": {"text": "A"}}],
            source_type="content",
            client_token="",
            user_id_type="open_id",
        )


def test_get_board_nodes_raises_when_credentials_exist_and_request_fails() -> None:
    class DummyResponse:
        def __init__(self, *, status_code: int, payload: dict[str, object]) -> None:
            self.status_code = status_code
            self._payload = payload
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if url.endswith("/whiteboards/wbcnERR/nodes"):
                return DummyResponse(
                    status_code=503,
                    payload={"code": 50301, "msg": "service unavailable"},
                )
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                status_code=200,
                payload={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
            )

    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=DummyHttpClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="HTTP 503"):
        client.get_board_nodes("wbcnERR")


def test_get_board_nodes_retries_when_doc_data_is_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        def __init__(self, *, status_code: int, payload: dict[str, object]) -> None:
            self.status_code = status_code
            self._payload = payload
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def __init__(self) -> None:
            self.calls = 0

        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if url.endswith("/whiteboards/wbcnREADY/nodes"):
                self.calls += 1
                if self.calls == 1:
                    return DummyResponse(
                        status_code=200,
                        payload={"code": 4003101, "msg": "doc data is not ready"},
                    )
                return DummyResponse(
                    status_code=200,
                    payload={"code": 0, "data": {"nodes": {"n1": {"id": "n1"}}}},
                )
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                status_code=200,
                payload={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
            )

    monkeypatch.setattr("app.modules.feishu.board_client.time.sleep", lambda _: None)
    http_client = DummyHttpClient()
    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=http_client,  # type: ignore[arg-type]
    )

    result = client.get_board_nodes("wbcnREADY")

    assert http_client.calls == 2
    assert result["data"]["nodes"]["n1"]["id"] == "n1"


def test_get_board_image_raises_when_credentials_exist_and_request_fails() -> None:
    class DummyResponse:
        def __init__(self, *, status_code: int, payload: dict[str, object] | None = None, content: bytes = b"") -> None:
            self.status_code = status_code
            self._payload = payload or {}
            self.headers: dict[str, str] = {}
            self.content = content or (json.dumps(self._payload).encode("utf-8") if self._payload else b"")

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if url.endswith("/whiteboards/wbcnIMG/download_as_image"):
                return DummyResponse(status_code=502)
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                status_code=200,
                payload={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
            )

    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=DummyHttpClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="HTTP 502"):
        client.get_board_image("wbcnIMG")


def test_get_board_image_retries_when_doc_data_is_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        def __init__(self, *, status_code: int, payload: dict[str, object] | None = None, content: bytes = b"") -> None:
            self.status_code = status_code
            self._payload = payload or {}
            self.headers: dict[str, str] = {}
            self.content = content or (json.dumps(self._payload).encode("utf-8") if self._payload else b"")

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyHttpClient:
        def __init__(self) -> None:
            self.calls = 0

        def request(self, method: str, url: str, json=None, headers=None):  # type: ignore[no-untyped-def]
            if url.endswith("/whiteboards/wbcnIMG/download_as_image"):
                self.calls += 1
                if self.calls == 1:
                    return DummyResponse(status_code=200, payload={"code": 4003101, "msg": "doc data is not ready"})
                return DummyResponse(status_code=200, content=b"png-bytes")
            raise AssertionError(url)

        def post(self, url: str, json=None):  # type: ignore[no-untyped-def]
            return DummyResponse(
                status_code=200,
                payload={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
            )

    monkeypatch.setattr("app.modules.feishu.board_client.time.sleep", lambda _: None)
    http_client = DummyHttpClient()
    client = FeishuBoardClient(
        settings=Settings(FEISHU_APP_ID="app", FEISHU_APP_SECRET="secret"),
        http_client=http_client,  # type: ignore[arg-type]
    )

    result = client.get_board_image("wbcnIMG")

    assert http_client.calls == 2
    assert result["preview_url"].startswith("data:image/png;base64,")


def test_do_with_retry_uses_default_total_attempts_when_non_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.feishu.board_client.time.sleep", lambda _: None)
    monkeypatch.setattr("app.modules.feishu.board_client.random.random", lambda: 0.0)
    client = FeishuBoardClient()
    calls = {"count": 0}

    def always_rate_limited():  # type: ignore[no-untyped-def]
        calls["count"] += 1
        error = RuntimeError("rate limit 429")
        setattr(error, "response_headers", {})
        raise error

    result = client._do_with_retry(  # type: ignore[attr-defined]
        always_rate_limited,
        max_retries=100,
        max_total_attempts=0,
        retry_on_rate_limit=True,
    )

    assert calls["count"] == 20
    assert result["attempts"] == 20
    assert "达到最大总尝试次数 20" in str(result["error"])


def test_do_with_retry_max_total_attempts_error_does_not_append_last_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.feishu.board_client.time.sleep", lambda _: None)
    monkeypatch.setattr("app.modules.feishu.board_client.random.random", lambda: 0.0)
    client = FeishuBoardClient()

    def always_rate_limited():  # type: ignore[no-untyped-def]
        error = RuntimeError("rate limit 429")
        setattr(error, "response_headers", {})
        raise error

    result = client._do_with_retry(  # type: ignore[attr-defined]
        always_rate_limited,
        max_retries=100,
        max_total_attempts=2,
        retry_on_rate_limit=True,
    )

    assert str(result["error"]) == "达到最大总尝试次数 2"


def test_do_with_retry_calls_on_retry_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.feishu.board_client.time.sleep", lambda _: None)
    monkeypatch.setattr("app.modules.feishu.board_client.random.random", lambda: 0.0)
    client = FeishuBoardClient()
    events: list[tuple[int, str, float]] = []
    calls = {"count": 0}

    def flaky():  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if calls["count"] == 1:
            error = RuntimeError("rate limit 429")
            setattr(error, "response_headers", {})
            raise error
        return "ok", {}

    result = client._do_with_retry(  # type: ignore[attr-defined]
        flaky,
        max_retries=1,
        max_total_attempts=2,
        retry_on_rate_limit=True,
        on_retry=lambda attempt, err, wait: events.append((attempt, str(err), wait)),
    )

    assert result["value"] == "ok"
    assert events
    assert events[0][0] == 1
    assert "rate limit 429" in events[0][1]


def test_do_with_retry_honors_cancel_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.feishu.board_client.time.sleep", lambda _: None)
    monkeypatch.setattr("app.modules.feishu.board_client.random.random", lambda: 0.0)
    client = FeishuBoardClient()
    state = {"cancelled": False}

    def always_retryable():  # type: ignore[no-untyped-def]
        error = RuntimeError("HTTP 503")
        setattr(error, "response_headers", {})
        raise error

    def cancel_check() -> bool:
        if state["cancelled"]:
            return True
        state["cancelled"] = True
        return False

    result = client._do_with_retry(  # type: ignore[attr-defined]
        always_retryable,
        max_retries=3,
        max_total_attempts=5,
        retry_on_rate_limit=False,
        cancel_check=cancel_check,
    )

    assert str(result["error"]) == "重试等待被取消"


def test_update_board_overwrite_succeeds_even_when_delete_old_nodes_fails() -> None:
    client = FeishuBoardClient()
    client.create_notes(
        "wbcnUPD",
        nodes_json_or_nodes=[{"type": "composite_shape", "text": {"text": "A"}}],
        source_type="content",
        client_token="",
        user_id_type="open_id",
    )

    original_delete = client.delete_board_nodes

    def failing_delete(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("delete failed")

    client.delete_board_nodes = failing_delete  # type: ignore[method-assign]
    try:
        result = client.update_board(
            "wbcnUPD",
            nodes_json_or_nodes=[{"type": "composite_shape", "text": {"text": "B"}}],
            overwrite=True,
            dry_run=False,
        )
    finally:
        client.delete_board_nodes = original_delete  # type: ignore[method-assign]

    assert result["created_count"] == 1
    assert result["deleted_count"] == 0
