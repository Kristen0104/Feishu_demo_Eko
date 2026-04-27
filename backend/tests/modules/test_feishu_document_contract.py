from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core import container
from app.config import Settings
from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.service import CanvasService
from app.modules.feishu import dependencies as feishu_dependencies
from app.modules.feishu.client import FeishuClient, HttpxFeishuHttpClient
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.service import FeishuService


class DummyResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = ""

    def json(self) -> dict[str, object]:
        return self._payload


class DummyHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def post(
        self,
        url: str,
        json: dict[str, object],
        timeout: int,
        headers: dict[str, str] | None = None,
    ) -> DummyResponse:
        self.calls.append(("POST", url))
        return DummyResponse(
            200,
            {
                "code": 0,
                "tenant_access_token": "tenant-token-001",
                "expire": 7200,
            },
        )

    def get(self, url: str, headers: dict[str, str], timeout: int) -> DummyResponse:
        self.calls.append(("GET", url))
        parsed_url = urlparse(url)
        query = parse_qs(parsed_url.query)
        if parsed_url.path.endswith("/nodes"):
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "node_id": "node-1",
                                "title": "Start",
                                "type": "text_shape",
                                "x": 120,
                                "y": 160,
                                "width": 240,
                                "height": 64,
                            },
                            {
                                "node_id": "node-2",
                                "title": "Discuss",
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
        if parsed_url.path.endswith("/blocks"):
            page_token = query.get("page_token", [""])[0]
            if page_token == "page-2":
                return DummyResponse(
                    200,
                    {
                        "code": 0,
                        "data": {
                            "items": [
                                {
                                    "block_id": "block-3",
                                    "block_type": 2,
                                    "text": {"elements": []},
                                },
                                {
                                    "block_id": "block-4",
                                    "block_type": 43,
                                    "board": {"token": "wb-second"},
                                },
                            ],
                            "page_token": "page-2",
                            "has_more": False,
                        },
                    },
                )
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "block_id": "block-1",
                                "block_type": 1,
                                "children": [],
                            },
                            {
                                "block_id": "block-2",
                                "block_type": 43,
                                "board": {"token": "wb-first"},
                            },
                        ],
                        "page_token": "page-2",
                        "has_more": True,
                    },
                },
            )
        if url.endswith("/raw_content"):
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "content": "需求收集\n方案设计\n执行计划",
                    },
                },
            )
        return DummyResponse(
            200,
            {
                "code": 0,
                "data": {
                    "title": "产品路线图",
                },
            },
        )


class ErroringHttpClient:
    def get(self, url: str, headers: dict[str, str], timeout: int) -> DummyResponse:
        return DummyResponse(
            503,
            {
                "code": 99991663,
                "msg": "upstream unavailable",
            },
        )


class MissingBoardTokenHttpClient:
    def get(self, url: str, headers: dict[str, str], timeout: int) -> DummyResponse:
        parsed_url = urlparse(url)
        if parsed_url.path.endswith("/blocks"):
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "block_id": "block-no-token",
                                "block_type": 43,
                                "board": {},
                            },
                            {
                                "block_id": "block-text",
                                "block_type": 2,
                            },
                        ],
                        "page_token": "",
                        "has_more": False,
                    },
                },
            )
        return DummyResponse(200, {"code": 0, "data": {}})


class BoardNodesErroringHttpClient(DummyHttpClient):
    def get(self, url: str, headers: dict[str, str], timeout: int) -> DummyResponse:
        parsed_url = urlparse(url)
        if parsed_url.path.endswith("/nodes"):
            return DummyResponse(
                200,
                {
                    "code": 99991677,
                    "msg": "board access denied",
                },
            )
        return super().get(url, headers, timeout)


class ConfusingWhiteboardIdHttpClient(DummyHttpClient):
    def get(self, url: str, headers: dict[str, str], timeout: int) -> DummyResponse:
        self.calls.append(("GET", url))
        parsed_url = urlparse(url)
        if parsed_url.path.endswith("/nodes"):
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "node_id": "node-from-board-token",
                                "title": "Resolved through board.token",
                            }
                        ]
                    },
                },
            )
        if parsed_url.path.endswith("/blocks"):
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "block": {
                                    "block_id": "block-id-must-not-be-used",
                                    "block_type": 43,
                                    "board": {"token": "whiteboard-token-from-board-token"},
                                }
                            }
                        ],
                        "page_token": "",
                        "has_more": False,
                    },
                },
            )
        if url.endswith("/raw_content"):
            return DummyResponse(200, {"code": 0, "data": {"content": "含画板文档"}})
        return DummyResponse(200, {"code": 0, "data": {"title": "混淆命名验证"}})


class RichTextWhiteboardNodesHttpClient(DummyHttpClient):
    def get(self, url: str, headers: dict[str, str], timeout: int) -> DummyResponse:
        self.calls.append(("GET", url))
        parsed_url = urlparse(url)
        if parsed_url.path.endswith("/nodes"):
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "node_id": "node-rich-1",
                                "type": "text_shape",
                                "text": {
                                    "elements": [
                                        {"text_run": {"content": "开始"}},
                                    ]
                                },
                            },
                            {
                                "node_id": "node-rich-2",
                                "type": "text_shape",
                                "rich_text": {
                                    "elements": [
                                        {"text_run": {"content": "是否继续"}},
                                    ]
                                },
                            },
                            {
                                "node_id": "node-rich-3",
                                "type": "composite_shape",
                                "title": {
                                    "angle": 0,
                                    "font_size": 14,
                                    "text": "执行",
                                },
                                "text": {
                                    "elements": [
                                        {"text_run": {"content": "执行-不应优先"}},
                                    ]
                                },
                            },
                            {
                                "node_id": "node-rich-4",
                                "type": "text_shape",
                                "text": "{'angle': 0, 'font_size': 14, 'text': '结束'}",
                            },
                            {
                                "id": "connector-rich-1",
                                "type": "connector",
                                "connector": {
                                    "shape": "curve",
                                    "start": {
                                        "attached_object": {"id": "node-rich-1"}
                                    },
                                    "end": {
                                        "attached_object": {"id": "node-rich-2"}
                                    },
                                    "captions": {
                                        "data": [
                                            {"text": "下一步"},
                                        ]
                                    },
                                },
                            },
                        ]
                    },
                },
            )
        return super().get(url, headers, timeout)


class RepeatingPageTokenHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, url: str, headers: dict[str, str], timeout: int) -> DummyResponse:
        self.calls.append(("GET", url))
        parsed_url = urlparse(url)
        query = parse_qs(parsed_url.query)
        current_page_token = query.get("page_token", [""])[0]
        next_page_token = current_page_token or "page-1"
        return DummyResponse(
            200,
            {
                "code": 0,
                "data": {
                    "items": [],
                    "page_token": next_page_token,
                    "has_more": True,
                },
            },
        )


def _build_client(feishu_service: FeishuService | None = None) -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    if feishu_service is not None:
        app.dependency_overrides[get_feishu_service] = lambda: feishu_service
    return TestClient(app)


def test_extract_document_token_from_share_url() -> None:
    client = FeishuClient(http_client=DummyHttpClient())

    token = client.extract_document_token(
        "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink"
    )

    assert token == "QFQVd8EEnoD58zxNwLNcmJRJnAg"


def test_resolve_document_share_returns_normalized_content() -> None:
    http_client = DummyHttpClient()
    client = FeishuClient(
        http_client=http_client,
        app_id="cli_test",
        app_secret="secret_test",
    )

    resolved = client.resolve_document_share(
        "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink"
    )

    assert resolved.document_token == "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    assert resolved.document_id == "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    assert resolved.title == "产品路线图"
    assert "需求收集" in resolved.plain_text
    assert resolved.share_url.startswith("https://jcneyh7qlo8i.feishu.cn/docx/")
    assert http_client.calls[0][0] == "POST"
    assert http_client.calls[1][0] == "GET"
    assert http_client.calls[2][0] == "GET"


def test_get_document_blocks_paginates_and_extracts_whiteboards() -> None:
    http_client = DummyHttpClient()
    client = FeishuClient(
        http_client=http_client,
        access_token_provider=lambda: "tenant-token-001",
    )

    resolved = client.get_document_blocks("doccnDemoToken")

    assert resolved.document_id == "doccnDemoToken"
    assert [block.block_id for block in resolved.blocks] == [
        "block-1",
        "block-2",
        "block-3",
        "block-4",
    ]
    assert [whiteboard.whiteboard_id for whiteboard in resolved.whiteboards] == [
        "wb-first",
        "wb-second",
    ]
    assert [whiteboard.block_id for whiteboard in resolved.whiteboards] == [
        "block-2",
        "block-4",
    ]
    assert http_client.calls == [
        (
            "GET",
            "https://open.feishu.cn/open-apis/docx/v1/documents/doccnDemoToken/blocks",
        ),
        (
            "GET",
            "https://open.feishu.cn/open-apis/docx/v1/documents/doccnDemoToken/blocks?page_token=page-2",
        ),
    ]


def test_get_document_blocks_ignores_whiteboard_blocks_without_board_token() -> None:
    client = FeishuClient(
        http_client=MissingBoardTokenHttpClient(),
        access_token_provider=lambda: "tenant-token-001",
    )

    resolved = client.get_document_blocks("doccnMissingBoardToken")

    assert resolved.document_id == "doccnMissingBoardToken"
    assert [block.block_id for block in resolved.blocks] == [
        "block-no-token",
        "block-text",
    ]
    assert resolved.whiteboards == []


def test_get_document_blocks_uses_board_token_not_block_id_for_whiteboard_id() -> None:
    http_client = ConfusingWhiteboardIdHttpClient()
    client = FeishuClient(
        http_client=http_client,
        access_token_provider=lambda: "tenant-token-001",
    )

    resolved = client.get_document_blocks("doccnConfusingIds")

    assert resolved.whiteboards[0].block_id == "block-id-must-not-be-used"
    assert resolved.whiteboards[0].whiteboard_id == "whiteboard-token-from-board-token"


def test_get_whiteboard_nodes_returns_normalized_nodes() -> None:
    client = FeishuClient(
        http_client=DummyHttpClient(),
        access_token_provider=lambda: "tenant-token-001",
    )

    resolved = client.get_whiteboard_nodes("wb-first")

    assert resolved.whiteboard_id == "wb-first"
    assert resolved.nodes[0]["node_id"] == "node-1"
    assert resolved.nodes[0]["title"] == "Start"
    assert resolved.nodes[0]["type"] == "text_shape"
    assert resolved.nodes[1]["node_id"] == "node-2"
    assert resolved.nodes[1]["width"] == 260


def test_resolve_document_whiteboard_import_payload_flattens_rich_text_nodes() -> None:
    service = FeishuService(
        FeishuClient(
            http_client=RichTextWhiteboardNodesHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )

    payload = service.resolve_document_whiteboard_import_payload(
        share_url="https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
        session_id="canvas-richtext-001",
    ).model_dump(mode="json")

    assert payload["source_board"]["nodes"][0]["id"] == "node-rich-1"
    assert payload["source_board"]["nodes"][0]["text"] == "开始"
    assert payload["source_board"]["nodes"][1]["id"] == "node-rich-2"
    assert payload["source_board"]["nodes"][1]["text"] == "是否继续"
    assert payload["source_board"]["nodes"][2]["id"] == "node-rich-3"
    assert payload["source_board"]["nodes"][2]["text"] == "执行"
    assert payload["source_board"]["nodes"][3]["id"] == "node-rich-4"
    assert payload["source_board"]["nodes"][3]["text"] == "结束"
    assert len(payload["source_board"]["nodes"]) == 4
    assert payload["source_board"]["edges"] == [
        {
            "id": "connector-rich-1",
            "from": "node-rich-1",
            "to": "node-rich-2",
            "type": "connector",
            "shape": "curve",
            "label": "下一步",
        }
    ]
    assert payload["working_board"]["latest_snapshot"]["nodes"][2]["text"] == "执行"
    assert payload["working_board"]["latest_snapshot"]["nodes"][3]["text"] == "结束"
    assert payload["working_board"]["latest_snapshot"]["edges"][0]["label"] == "下一步"


def test_get_feishu_http_client_returns_httpx_transport() -> None:
    http_client = feishu_dependencies.get_feishu_http_client()

    assert isinstance(http_client, HttpxFeishuHttpClient)
    http_client.close()


def test_default_dependency_route_uses_http_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    http_client = DummyHttpClient()
    monkeypatch.setattr(
        feishu_dependencies,
        "get_feishu_http_client",
        lambda: http_client,
    )
    monkeypatch.setattr(
        feishu_dependencies,
        "get_settings",
        lambda: Settings(FEISHU_DOC_ACCESS_TOKEN="tenant-token-001"),
    )
    client = _build_client()

    response = client.post(
        "/api/v1/feishu/documents/resolve",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["title"] == "产品路线图"
    assert payload["title"] != "Stub Feishu Document"
    assert http_client.calls == [
        (
            "GET",
            "https://open.feishu.cn/open-apis/docx/v1/documents/QFQVd8EEnoD58zxNwLNcmJRJnAg",
        ),
        (
            "GET",
            "https://open.feishu.cn/open-apis/docx/v1/documents/QFQVd8EEnoD58zxNwLNcmJRJnAg/raw_content",
        ),
    ]


def test_resolve_document_share_raises_on_upstream_error() -> None:
    client = FeishuClient(
        http_client=ErroringHttpClient(),
        access_token_provider=lambda: "tenant-token-001",
    )

    with pytest.raises(HTTPException) as excinfo:
        client.resolve_document_share(
            "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink"
        )

    assert excinfo.value.status_code == 502


def test_get_document_blocks_raises_when_page_token_does_not_advance() -> None:
    client = FeishuClient(
        http_client=RepeatingPageTokenHttpClient(),
        access_token_provider=lambda: "tenant-token-001",
    )

    with pytest.raises(HTTPException) as excinfo:
        client.get_document_blocks("doccnLoopingToken")

    assert excinfo.value.status_code == 502


def test_resolve_document_whiteboard_nodes_raises_when_no_whiteboard_is_discovered() -> None:
    service = FeishuService(
        client=FeishuClient(
            http_client=MissingBoardTokenHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )

    with pytest.raises(HTTPException) as excinfo:
        service.resolve_document_whiteboard_nodes(
            "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg"
        )

    assert excinfo.value.status_code == 404


def test_resolve_document_whiteboard_nodes_raises_on_board_nodes_upstream_error() -> None:
    service = FeishuService(
        client=FeishuClient(
            http_client=BoardNodesErroringHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )

    with pytest.raises(HTTPException) as excinfo:
        service.resolve_document_whiteboard_nodes(
            "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg"
        )

    assert excinfo.value.status_code == 502


def test_feishu_document_resolve_route_returns_document_content() -> None:
    http_client = DummyHttpClient()
    feishu_service = FeishuService(
        client=FeishuClient(
            http_client=http_client,
            app_id="cli_test",
            app_secret="secret_test",
        )
    )
    client = _build_client(feishu_service)

    response = client.post(
        "/api/v1/feishu/documents/resolve",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["document_token"] == "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    assert payload["document_id"] == "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    assert payload["title"] == "产品路线图"
    assert "方案设计" in payload["plain_text"]


def test_feishu_document_blocks_route_returns_normalized_blocks() -> None:
    feishu_service = FeishuService(
        client=FeishuClient(
            http_client=DummyHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )
    client = _build_client(feishu_service)

    response = client.get("/api/v1/feishu/documents/doccnDemoToken/blocks")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["document_id"] == "doccnDemoToken"
    assert [block["block_id"] for block in payload["blocks"]] == [
        "block-1",
        "block-2",
        "block-3",
        "block-4",
    ]
    assert payload["whiteboards"] == [
        {"whiteboard_id": "wb-first", "block_id": "block-2"},
        {"whiteboard_id": "wb-second", "block_id": "block-4"},
    ]


def test_feishu_document_whiteboard_nodes_route_returns_normalized_payload() -> None:
    feishu_service = FeishuService(
        client=FeishuClient(
            http_client=DummyHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )
    client = _build_client(feishu_service)

    response = client.post(
        "/api/v1/feishu/documents/resolve-whiteboard-nodes",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["document_id"] == "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    assert payload["whiteboard_id"] == "wb-first"
    assert payload["block_id"] == "block-2"
    assert payload["nodes"][0]["node_id"] == "node-1"
    assert payload["nodes"][0]["title"] == "Start"
    assert payload["nodes"][0]["type"] == "text_shape"
    assert payload["nodes"][1]["node_id"] == "node-2"


def test_resolve_document_whiteboard_nodes_uses_board_token_for_nodes_request() -> None:
    http_client = ConfusingWhiteboardIdHttpClient()
    service = FeishuService(
        client=FeishuClient(
            http_client=http_client,
            access_token_provider=lambda: "tenant-token-001",
        )
    )

    resolved = service.resolve_document_whiteboard_nodes(
        "https://jcneyh7qlo8i.feishu.cn/docx/confusingDocumentToken"
    )

    assert resolved.document_id == "confusingDocumentToken"
    assert resolved.block_id == "block-id-must-not-be-used"
    assert resolved.whiteboard_id == "whiteboard-token-from-board-token"
    assert resolved.nodes[0]["node_id"] == "node-from-board-token"
    assert (
        "https://open.feishu.cn/open-apis/board/v1/whiteboards/"
        "whiteboard-token-from-board-token/nodes"
    ) in [url for method, url in http_client.calls if method == "GET"]
    assert all("block-id-must-not-be-used/nodes" not in url for _, url in http_client.calls)


def test_feishu_document_whiteboards_discovery_route_returns_smoke_test_ids() -> None:
    feishu_service = FeishuService(
        client=FeishuClient(
            http_client=ConfusingWhiteboardIdHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )
    client = _build_client(feishu_service)

    response = client.post(
        "/api/v1/feishu/documents/resolve-whiteboards",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/confusingDocumentToken",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["document_id"] == "confusingDocumentToken"
    assert payload["title"] == "混淆命名验证"
    assert payload["whiteboards"] == [
        {
            "block_id": "block-id-must-not-be-used",
            "whiteboard_id": "whiteboard-token-from-board-token",
        }
    ]


def test_feishu_document_whiteboard_import_route_returns_adapter_payload() -> None:
    feishu_service = FeishuService(
        client=FeishuClient(
            http_client=DummyHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )
    client = _build_client(feishu_service)

    response = client.post(
        "/api/v1/feishu/documents/resolve-whiteboard-import",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
            "session_id": "canvas-feishu-005",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["session_id"] == "canvas-feishu-005"
    assert payload["source_board"]["board_id"] == "wb-first"
    assert payload["source_board"]["title"] == "产品路线图"
    assert payload["source_board"]["nodes"][0]["id"] == "node-1"
    assert payload["source_board"]["nodes"][0]["text"] == "Start"
    assert payload["source_board"]["nodes"][0]["type"] == "text_shape"
    assert payload["source_board"]["nodes"][1]["id"] == "node-2"
    assert payload["source_board"]["nodes"][1]["text"] == "Discuss"
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "Start"


def test_feishu_document_resolve_route_returns_upstream_failure() -> None:
    feishu_service = FeishuService(
        client=FeishuClient(
            http_client=ErroringHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )
    client = _build_client(feishu_service)

    response = client.post(
        "/api/v1/feishu/documents/resolve",
        json={
            "share_url": "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink",
        },
    )

    assert response.status_code == 502


def test_canvas_can_build_generation_context_from_resolved_document() -> None:
    feishu_service = FeishuService(client=FeishuClient())
    document = feishu_service.resolve_document_content(
        "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg"
    )
    canvas_service = CanvasService(repository=CanvasRepository())

    generation_request = canvas_service.build_generation_request_from_feishu_document(
        document,
        user_prompt="根据这份文档生成画板",
    )

    assert generation_request.generation_mode == "full_board"
    assert generation_request.user_prompt == "根据这份文档生成画板"
    assert generation_request.chat_context[0]["content"] == "文档标题: Stub Feishu Document"
    assert "QFQVd8EEnoD58zxNwLNcmJRJnAg" in generation_request.chat_context[1]["content"]
    assert generation_request.board_context["source_document"]["document_token"] == (
        "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    )
