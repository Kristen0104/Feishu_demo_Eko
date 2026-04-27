from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container


def _build_client() -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    return TestClient(app)


def test_feishu_board_import_endpoint_returns_cli_like_payload() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/feishu/board/import",
        json={
            "whiteboard_id": "wbcn123",
            "source": "flowchart TD\nA-->B",
            "source_type": "content",
            "syntax": "mermaid",
            "diagram_type": "flowchart",
            "style": "board",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["whiteboard_id"] == "wbcn123"
    assert payload["data"]["syntax"] == "mermaid"
    assert payload["data"]["diagram_type"] == "flowchart"


def test_feishu_board_create_notes_and_nodes_endpoint_roundtrip() -> None:
    client = _build_client()

    create_response = client.post(
        "/api/v1/feishu/board/create-notes",
        json={
            "whiteboard_id": "wbcn123",
            "nodes": [{"type": "composite_shape", "text": {"text": "A"}}],
            "client_token": "",
            "user_id_type": "open_id",
        },
    )
    assert create_response.status_code == 200

    nodes_response = client.get("/api/v1/feishu/board/nodes/wbcn123")
    assert nodes_response.status_code == 200
    payload = nodes_response.json()
    assert payload["data"]["nodes"]


def test_feishu_board_update_delete_and_image_endpoints() -> None:
    client = _build_client()
    client.post(
        "/api/v1/feishu/board/create-notes",
        json={
            "whiteboard_id": "wbcn456",
            "nodes": [{"type": "composite_shape", "text": {"text": "A"}}],
            "source_type": "content",
            "client_token": "",
            "user_id_type": "open_id",
        },
    )

    update_response = client.post(
        "/api/v1/feishu/board/update",
        json={
            "whiteboard_id": "wbcn456",
            "nodes": [{"type": "composite_shape", "text": {"text": "B"}}],
            "overwrite": True,
            "dry_run": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["created_count"] == 1

    image_response = client.get("/api/v1/feishu/board/image/wbcn456")
    assert image_response.status_code == 200
    assert image_response.json()["data"]["preview_url"] == "https://stub.preview/wbcn456.png"

    delete_response = client.post(
        "/api/v1/feishu/board/delete",
        json={"whiteboard_id": "wbcn456", "all": True},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted_count"] >= 1
