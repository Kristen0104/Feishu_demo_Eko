from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container


def _build_client() -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    return TestClient(app)


def test_run_board_task_executes_and_returns_preview() -> None:
    client = _build_client()

    create_response = client.post(
        "/api/v1/canvas/board/tasks",
        json={
            "message": "帮我画一个 AI 网关架构图",
            "sharing_url": "https://example.feishu.cn/wiki/board/wbcnARCH",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    response = client.post(f"/api/v1/canvas/board/tasks/{task_id}/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "succeeded"
    assert payload["data"]["whiteboard_id"] == "wbcnARCH"
    assert payload["data"]["preview_url"] == "https://stub.preview/wbcnARCH.png"
    assert payload["data"]["node_ids"]
    assert len(payload["data"]["node_ids"]) >= 10
    assert payload["data"]["deleted_count"] == 0
    assert any(log["step"] == "planning" for log in payload["data"]["logs"])
    assert any("画板预览已生成" in log["message"] for log in payload["data"]["logs"])


def test_board_ui_page_renders_form_and_actions() -> None:
    client = _build_client()

    response = client.get("/canvas/board")

    assert response.status_code == 200
    assert "Feishu Board Generator" in response.text
    assert "sharing_url" in response.text
    assert "message" in response.text
    assert "syntax" in response.text
    assert "diagram_type" in response.text
    assert "style" in response.text
    assert "overwrite" in response.text
    assert "dry_run" in response.text
    assert "Run Task" in response.text
