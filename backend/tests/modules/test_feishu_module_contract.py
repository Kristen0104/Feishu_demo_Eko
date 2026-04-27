from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.service import FeishuService
from tests.modules.test_feishu_document_contract import DummyHttpClient, DummyResponse


def _build_client(feishu_service: FeishuService | None = None) -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    if feishu_service is not None:
        app.dependency_overrides[get_feishu_service] = lambda: feishu_service
    return TestClient(app)


def test_feishu_board_import_and_export_routes_round_trip_payload() -> None:
    client = _build_client(FeishuService(client=FeishuClient()))
    payload = {
        "session_id": "feishu-session-001",
        "source_board": {
            "board_id": "source-board-100",
            "title": "飞书画板",
            "nodes": [{"id": "node-1", "text": "节点文本"}],
            "edges": [
                {"id": "edge-1", "from": "node-1", "to": "node-1", "type": "self"}
            ],
        },
        "element_mappings": [
            {
                "source_element_id": "node-1",
                "working_element_id": "node-1",
                "element_type": "node",
            }
        ],
    }

    import_response = client.post("/api/v1/feishu/boards/import", json=payload)

    assert import_response.status_code == 200
    imported = import_response.json()["data"]
    assert imported["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "节点文本"

    export_response = client.post("/api/v1/feishu/boards/export", json=imported)

    assert export_response.status_code == 200
    exported = export_response.json()["data"]
    assert exported["source_board"]["board_id"] == "source-board-100"
    assert exported["source_board"]["nodes"][0]["text"] == "节点文本"
    assert exported["source_board"]["edges"][0]["to"] == "node-1"

    publish_response = client.post("/api/v1/feishu/boards/publish", json=imported)

    assert publish_response.status_code == 200
    published = publish_response.json()["data"]
    assert published["mode"] == "adapter_only"
    assert published["accepted"] is True
    assert published["board_id"] == "source-board-100"
    assert published["exported_board"]["source_board"]["nodes"][0]["text"] == "节点文本"


class PublishableDummyHttpClient(DummyHttpClient):
    def __init__(self, *, existing_nodes: list[dict[str, object]] | None = None) -> None:
        super().__init__()
        self.existing_nodes = existing_nodes or []
        self.post_payloads: list[tuple[str, dict[str, object]]] = []

    def post(
        self,
        url: str,
        json: dict[str, object],
        timeout: int,
        headers: dict[str, str] | None = None,
    ) -> DummyResponse:
        self.calls.append(("POST", url))
        self.post_payloads.append((url, json))
        if url.endswith("/update_theme"):
            return DummyResponse(200, {"code": 0, "data": {}})
        if url.endswith("/nodes"):
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "node_ids": ["created-1"],
                    },
                },
            )
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
        if url.endswith("/nodes"):
            return DummyResponse(
                200,
                {
                    "code": 0,
                    "data": {
                        "items": self.existing_nodes,
                    },
                },
            )
        return DummyResponse(200, {"code": 0, "data": {}})


def test_feishu_board_publish_uses_upstream_create_nodes_when_endpoint_is_configured() -> None:
    http_client = PublishableDummyHttpClient()
    client = _build_client(
        FeishuService(
            client=FeishuClient(
                http_client=http_client,
                access_token_provider=lambda: "tenant-token-001",
                whiteboard_publish_endpoint_template=(
                    "https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes"
                ),
            )
        )
    )

    response = client.post(
        "/api/v1/feishu/boards/publish",
        json={
            "session_id": "feishu-session-002",
            "source_board": {
                "board_id": "source-board-200",
                "title": "飞书画板",
                "nodes": [{"id": "node-1", "text": "节点文本"}],
                "edges": [
                    {"id": "edge-1", "from": "node-1", "to": "node-1", "type": "self"}
                ],
                "metadata": {"theme": "classic"},
            },
        },
    )

    assert response.status_code == 200
    published = response.json()["data"]
    assert published["mode"] == "upstream"
    assert published["accepted"] is True
    assert published["upstream_payload"]["create_nodes"]["node_ids"] == ["created-1"]
    create_request = next(body for url, body in http_client.post_payloads if url.endswith("/nodes"))
    assert create_request["nodes"][0]["type"] == "composite_shape"
    assert create_request["nodes"][0]["composite_shape"]["type"] == "round_rect"
    assert create_request["nodes"][0]["text"]["text"] == "节点文本"
    assert create_request["nodes"][1]["type"] == "connector"
    assert create_request["nodes"][1]["connector"]["shape"] == "right_angled_polyline"
    assert create_request["nodes"][1]["connector"]["end"]["arrow_style"] == "triangle_arrow"
    theme_request = next(body for url, body in http_client.post_payloads if url.endswith("/update_theme"))
    assert theme_request == {"theme": "classic"}


def test_feishu_board_publish_rejects_non_empty_target_board() -> None:
    http_client = PublishableDummyHttpClient(existing_nodes=[{"node_id": "existing-1"}])
    client = _build_client(
        FeishuService(
            client=FeishuClient(
                http_client=http_client,
                access_token_provider=lambda: "tenant-token-001",
                whiteboard_publish_endpoint_template=(
                    "https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes"
                ),
            )
        )
    )

    response = client.post(
        "/api/v1/feishu/boards/publish",
        json={
            "session_id": "feishu-session-003",
            "source_board": {
                "board_id": "source-board-300",
                "title": "飞书画板",
                "nodes": [{"id": "node-1", "text": "节点文本"}],
                "edges": [],
            },
        },
    )

    assert response.status_code == 200
    published = response.json()["data"]
    assert published["mode"] == "upstream"
    assert published["accepted"] is False
    assert published["upstream_payload"]["reason"] == "target_board_not_empty"


def test_feishu_board_publish_maps_visual_roles_and_styles_to_feishu_nodes() -> None:
    http_client = PublishableDummyHttpClient()
    client = _build_client(
        FeishuService(
            client=FeishuClient(
                http_client=http_client,
                access_token_provider=lambda: "tenant-token-001",
                whiteboard_publish_endpoint_template=(
                    "https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes"
                ),
            )
        )
    )

    response = client.post(
        "/api/v1/feishu/boards/publish",
        json={
            "session_id": "feishu-session-004",
            "source_board": {
                "board_id": "source-board-400",
                "title": "飞书流程图",
                "nodes": [
                    {
                        "id": "start-node",
                        "text": "开始",
                        "x": 100,
                        "y": 100,
                        "width": 220,
                        "height": 80,
                        "visual_role": "start",
                        "theme_fill_color_code": 3,
                        "theme_border_color_code": 5,
                        "font_size": 18,
                        "font_weight": "bold",
                    },
                    {
                        "id": "decision-node",
                        "text": "是否继续",
                        "x": 420,
                        "y": 100,
                        "width": 220,
                        "height": 100,
                        "visual_role": "decision",
                        "fill_color": "#FFF7E8",
                        "border_style": "dash",
                        "border_width": "medium",
                    },
                ],
                "edges": [
                    {
                        "id": "edge-1",
                        "from": "start-node",
                        "to": "decision-node",
                        "label": "下一步",
                        "shape": "right_angled_polyline",
                        "turning_points": [{"x": 40, "y": 0}],
                        "border_style": "solid",
                        "border_width": "medium",
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    create_request = next(body for url, body in http_client.post_payloads if url.endswith("/nodes"))
    start_node = create_request["nodes"][0]
    decision_node = create_request["nodes"][1]
    connector = create_request["nodes"][2]

    assert start_node["composite_shape"]["type"] == "state_start"
    assert start_node["style"]["theme_fill_color_code"] == 3
    assert start_node["style"]["theme_border_color_code"] == 5
    assert start_node["text"]["font_size"] == 18
    assert start_node["text"]["font_weight"] == "bold"

    assert decision_node["composite_shape"]["type"] == "flow_chart_diamond"
    assert decision_node["style"]["fill_color"] == "#FFF7E8"
    assert decision_node["style"]["border_style"] == "dash"
    assert decision_node["style"]["border_width"] == "medium"

    assert connector["type"] == "connector"
    assert connector["connector"]["shape"] == "right_angled_polyline"
    assert connector["connector"]["turning_points"] == [{"x": 40.0, "y": 0.0}]
    assert connector["connector"]["captions"]["data"][0]["text"] == "下一步"
    assert connector["connector"]["start"]["attached_object"]["snap_to"] == "right"
    assert connector["connector"]["end"]["attached_object"]["snap_to"] == "left"
    assert connector["connector"]["start"]["arrow_style"] == "none"
    assert connector["connector"]["end"]["arrow_style"] == "triangle_arrow"


def test_feishu_board_publish_maps_official_text_style_and_connector_options() -> None:
    http_client = PublishableDummyHttpClient()
    client = _build_client(
        FeishuService(
            client=FeishuClient(
                http_client=http_client,
                access_token_provider=lambda: "tenant-token-001",
                whiteboard_publish_endpoint_template=(
                    "https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes"
                ),
            )
        )
    )

    response = client.post(
        "/api/v1/feishu/boards/publish",
        json={
            "session_id": "feishu-session-005",
            "source_board": {
                "board_id": "source-board-500",
                "title": "飞书流程图",
                "nodes": [
                    {
                        "id": "node-1",
                        "text": "基础图形",
                        "x": 100,
                        "y": 100,
                        "text_angle": 90,
                        "line_through": True,
                        "text_color_type": 0,
                        "text_background_color_type": 1,
                        "fill_color_type": 0,
                        "border_color_type": 1,
                    },
                    {
                        "id": "node-2",
                        "text": "下一步",
                        "x": 360,
                        "y": 100,
                    },
                ],
                "edges": [
                    {
                        "id": "edge-1",
                        "from": "node-1",
                        "to": "node-2",
                        "label": "通过",
                        "shape": "not-a-feishu-shape",
                        "start_arrow_style": "circle_arrow",
                        "end_arrow_style": "bad-arrow",
                        "caption_auto_direction": False,
                        "caption_position": 0.25,
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    create_request = next(body for url, body in http_client.post_payloads if url.endswith("/nodes"))
    shape_node = create_request["nodes"][0]
    connector = create_request["nodes"][2]["connector"]

    assert shape_node["text"]["angle"] == 90
    assert shape_node["text"]["line_through"] is True
    assert shape_node["text"]["text_color_type"] == 0
    assert shape_node["text"]["text_background_color_type"] == 1
    assert shape_node["style"]["fill_color_type"] == 0
    assert shape_node["style"]["border_color_type"] == 1
    assert connector["shape"] == "right_angled_polyline"
    assert connector["start"]["arrow_style"] == "circle_arrow"
    assert connector["end"]["arrow_style"] == "triangle_arrow"
    assert connector["caption_auto_direction"] is False
    assert connector["caption_position"] == 0.25
    assert connector["start"]["attached_object"]["position"] == {"x": 1.0, "y": 0.5}
    assert connector["end"]["attached_object"]["position"] == {"x": 0.0, "y": 0.5}


def test_feishu_board_publish_maps_section_sticky_note_and_mind_map_nodes() -> None:
    http_client = PublishableDummyHttpClient()
    client = _build_client(
        FeishuService(
            client=FeishuClient(
                http_client=http_client,
                access_token_provider=lambda: "tenant-token-001",
                whiteboard_publish_endpoint_template=(
                    "https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes"
                ),
            )
        )
    )

    response = client.post(
        "/api/v1/feishu/boards/publish",
        json={
            "session_id": "feishu-session-006",
            "source_board": {
                "board_id": "source-board-600",
                "title": "飞书画板结构节点",
                "nodes": [
                    {
                        "id": "section-1",
                        "type": "section",
                        "title": "阶段一",
                        "x": 80,
                        "y": 80,
                        "width": 480,
                        "height": 240,
                    },
                    {
                        "id": "note-1",
                        "type": "sticky_note",
                        "text": "待确认",
                        "x": 120,
                        "y": 140,
                        "user_id": "ou_test_user",
                        "show_author_info": False,
                        "theme_fill_color_code": 3,
                    },
                    {
                        "id": "mind-root",
                        "type": "mind_map",
                        "text": "主题",
                        "mind_map_role": "root",
                        "mind_map_layout": "tree_right",
                        "line_style": "right_angle",
                    },
                    {
                        "id": "mind-child",
                        "type": "mind_map",
                        "text": "子主题",
                        "parent_id": "mind-root",
                        "layout_position": "right",
                        "z_index": 2,
                    },
                ],
                "edges": [],
            },
        },
    )

    assert response.status_code == 200
    create_request = next(body for url, body in http_client.post_payloads if url.endswith("/nodes"))
    section, sticky_note, mind_root, mind_child = create_request["nodes"]

    assert section["type"] == "section"
    assert "text" not in section
    assert section["section"] == {"title": "阶段一"}
    assert sticky_note["type"] == "sticky_note"
    assert sticky_note["text"]["text"] == "待确认"
    assert sticky_note["sticky_note"] == {
        "user_id": "ou_test_user",
        "show_author_info": False,
    }
    assert sticky_note["style"] == {"theme_fill_color_code": 3}
    assert mind_root["mind_map_root"] == {
        "layout": "tree_right",
        "type": "mind_map_round_rect",
        "line_style": "right_angle",
    }
    assert mind_child["mind_map_node"] == {
        "parent_id": "mind-root",
        "type": "mind_map_text",
        "z_index": 2,
        "layout_position": "right",
    }


def test_feishu_board_syntax_import_calls_official_plantuml_endpoint() -> None:
    http_client = PublishableDummyHttpClient()
    client = _build_client(
        FeishuService(
            client=FeishuClient(
                http_client=http_client,
                access_token_provider=lambda: "tenant-token-001",
            )
        )
    )

    response = client.post(
        "/api/v1/feishu/boards/source-board-700/syntax-import",
        json={
            "code": "graph TD; A-->B;",
            "syntax_type": 2,
            "style_type": 1,
            "diagram_type": 0,
        },
    )

    assert response.status_code == 200
    url, body = http_client.post_payloads[-1]
    assert url == (
        "https://open.feishu.cn/open-apis/board/v1/whiteboards/"
        "source-board-700/nodes/plantuml"
    )
    assert body == {
        "plant_uml_code": "graph TD; A-->B;",
        "style_type": 1,
        "syntax_type": 2,
        "diagram_type": 0,
    }


def test_feishu_board_mermaid_import_calls_official_syntax_endpoint() -> None:
    http_client = PublishableDummyHttpClient()
    client = _build_client(
        FeishuService(
            client=FeishuClient(
                http_client=http_client,
                access_token_provider=lambda: "tenant-token-001",
            )
        )
    )

    response = client.post(
        "/api/v1/feishu/boards/source-board-701/mermaid-import",
        json={
            "code": "graph TD; A-->B;",
            "style_type": 1,
            "diagram_type": 0,
        },
    )

    assert response.status_code == 200
    url, body = http_client.post_payloads[-1]
    assert url == (
        "https://open.feishu.cn/open-apis/board/v1/whiteboards/"
        "source-board-701/nodes/plantuml"
    )
    assert body == {
        "plant_uml_code": "graph TD; A-->B;",
        "style_type": 1,
        "syntax_type": 2,
        "diagram_type": 0,
    }
