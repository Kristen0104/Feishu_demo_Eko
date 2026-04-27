from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container


def _build_client() -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    return TestClient(app)


def test_create_board_task_returns_pending_task() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/canvas/board/tasks",
        json={
            "message": "帮我画一个 AI 应用架构图",
            "sharing_url": "https://example.feishu.cn/wiki/board/wbcnAABBCC",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "pending"
    assert payload["data"]["current_step"] == "pending"
    assert payload["data"]["message"] == "帮我画一个 AI 应用架构图"
    assert payload["data"]["sharing_url"] == "https://example.feishu.cn/wiki/board/wbcnAABBCC"
    assert payload["data"]["render_mode"] == "create_notes"
    assert payload["data"]["ticket_id"] is None
    assert payload["data"]["node_ids"] == []
    assert payload["data"]["deleted_count"] == 0
    assert payload["data"]["logs"] == []


def test_get_board_task_returns_latest_task_state() -> None:
    client = _build_client()

    create_response = client.post(
        "/api/v1/canvas/board/tasks",
        json={
            "message": "帮我画一个流程图",
            "sharing_url": "https://example.feishu.cn/docx/AbCdEfGhIjKl",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    response = client.get(f"/api/v1/canvas/board/tasks/{task_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["task_id"] == task_id
    assert payload["data"]["status"] == "pending"
    assert payload["data"]["render_mode"] == "import_diagram"
