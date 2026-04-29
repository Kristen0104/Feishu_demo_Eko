from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.agent.service import SyncSubagent
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.router import router as feishu_router


class RecordingFeishuService:
    def __init__(self) -> None:
        self.ticket_calls: list[tuple[str, str]] = []
        self.background_calls: list[dict[str, str | None]] = []
        self.publish_calls: list[dict[str, str | None]] = []
        self.status_calls: list[str] = []

    async def create_import_ticket(self, markdown_content: str, title: str) -> str:
        self.ticket_calls.append((markdown_content, title))
        return "ticket-123"

    async def publish_markdown_background(
        self,
        session_id: str,
        title: str,
        markdown_content: str,
        app_token: str | None = None,
        table_id: str | None = None,
        ticket: str | None = None,
    ) -> None:
        self.background_calls.append(
            {
                "session_id": session_id,
                "title": title,
                "markdown_content": markdown_content,
                "app_token": app_token,
                "table_id": table_id,
                "ticket": ticket,
            }
        )

    async def publish_markdown_to_feishu(
        self,
        title: str,
        markdown_content: str,
        app_token: str | None = None,
        table_id: str | None = None,
        ticket: str | None = None,
    ) -> dict[str, str | None]:
        self.publish_calls.append(
            {
                "title": title,
                "markdown_content": markdown_content,
                "app_token": app_token,
                "table_id": table_id,
                "ticket": ticket,
            }
        )
        return {
            "ticket": ticket or "ticket-456",
            "document_url": "https://feishu.cn/doc/abc",
            "record_id": "record-123",
            "status": "success",
        }

    def get_import_status(self, ticket: str) -> dict[str, str | None]:
        self.status_calls.append(ticket)
        return {
            "ticket": ticket,
            "status": "failed",
            "document_url": None,
        }


def test_publish_route_creates_single_ticket_and_reuses_it() -> None:
    service = RecordingFeishuService()
    app = FastAPI()
    app.include_router(feishu_router, prefix="/api/v1/feishu")
    app.dependency_overrides[get_feishu_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/feishu/sync/publish",
            json={
                "session_id": "session-1",
                "title": "Weekly Report",
                "markdown_content": "# report",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["ticket"] == "ticket-123"
    assert service.ticket_calls == [("# report", "Weekly Report")]
    assert service.background_calls == [
        {
            "session_id": "session-1",
            "title": "Weekly Report",
            "markdown_content": "# report",
            "app_token": None,
            "table_id": None,
            "ticket": "ticket-123",
        }
    ]


def test_status_route_exposes_failed_import_status() -> None:
    service = RecordingFeishuService()
    app = FastAPI()
    app.include_router(feishu_router, prefix="/api/v1/feishu")
    app.dependency_overrides[get_feishu_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/feishu/sync/status/ticket-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == {
        "ticket": "ticket-123",
        "status": "failed",
        "document_url": None,
    }
    assert service.status_calls == ["ticket-123"]


def test_agent_sync_subagent_reuses_feishu_service() -> None:
    service = RecordingFeishuService()
    sync_subagent = SyncSubagent(service)

    document_url, record_id = asyncio.run(
        sync_subagent.sync_to_feishu(
            title="Weekly Report",
            content="# report",
            app_token="app-token",
            table_id="table-id",
        )
    )

    assert (document_url, record_id) == ("https://feishu.cn/doc/abc", "record-123")
    assert service.publish_calls == [
        {
            "title": "Weekly Report",
            "markdown_content": "# report",
            "app_token": "app-token",
            "table_id": "table-id",
            "ticket": None,
        }
    ]
