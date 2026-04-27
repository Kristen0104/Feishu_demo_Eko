from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container


def _build_client() -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    return TestClient(app)


def test_canvas_working_board_updates_persist_across_requests() -> None:
    client = _build_client()

    first = client.get("/api/v1/canvas/sessions/session-001/working-board")
    assert first.status_code == 200
    assert first.json()["data"]["latest_version"] == 1
    assert first.json()["data"]["offline_state"] == "clean"

    update = client.post(
        "/api/v1/canvas/sessions/session-001/changes",
        json={
            "change_id": "change-001",
            "session_id": "session-001",
            "change_type": "user_edit",
            "actor_type": "user",
            "payload": {
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "新增节点"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "新增节点"}]},
            },
            "base_version": "v1",
            "result_version": "v2",
        },
    )
    assert update.status_code == 200
    assert update.json()["data"]["latest_version"] == 2
    assert update.json()["data"]["latest_snapshot"]["nodes"][0]["text"] == "新增节点"

    second = client.get("/api/v1/canvas/sessions/session-001/working-board")
    assert second.status_code == 200
    assert second.json()["data"]["latest_version"] == 2
    assert second.json()["data"]["latest_snapshot"]["nodes"][0]["text"] == "新增节点"


def test_canvas_change_history_records_applied_changes() -> None:
    client = _build_client()

    client.post(
        "/api/v1/canvas/sessions/session-002/changes",
        json={
            "change_id": "change-002",
            "session_id": "session-002",
            "change_type": "ai_patch",
            "actor_type": "ai",
            "payload": {
                "latest_snapshot": {"nodes": [{"id": "node-2", "text": "AI 补丁"}]},
            },
        },
    )

    history = client.get("/api/v1/canvas/sessions/session-002/changes")
    assert history.status_code == 200
    assert history.json()["data"][0]["change_id"] == "change-002"
    assert history.json()["data"][0]["change_type"] == "ai_patch"
