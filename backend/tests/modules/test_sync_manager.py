from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container
from app.modules.sync.dependencies import get_sync_service
from app.modules.sync.manager import SyncConnectionManager
from app.modules.sync.manager import SessionRecord
from app.modules.sync.service import SyncService


def test_delete_session_removes_in_memory_record() -> None:
    manager = SyncConnectionManager()

    async def run() -> None:
        await manager.register_session(
            "session-1",
            source="feishu",
            title="测试会话",
            summary="测试摘要",
        )
        assert await manager.get_session("session-1") is not None
        assert await manager.delete_session("session-1") is True
        assert await manager.get_session("session-1") is None

    asyncio.run(run())


def test_delete_sync_session_is_idempotent() -> None:
    app = FastAPI()
    container.register_routers(app)
    service = SyncService()
    app.dependency_overrides[get_sync_service] = lambda: service

    async def seed() -> None:
        await service.register_session(
            "session-1",
            source="feishu",
            title="测试会话",
            summary="测试摘要",
        )

    asyncio.run(seed())

    with TestClient(app) as client:
        response = client.delete("/api/v1/sync/sessions/session-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["session_id"] == "session-1"
    assert payload["data"]["deleted"] is True


def test_publish_task_completed_persists_intent_artifact_and_messages() -> None:
    manager = SyncConnectionManager()
    service = SyncService(manager=manager)

    async def run() -> None:
        await service.register_session(
            "session-1",
            source="feishu",
            title="测试会话",
            summary="测试摘要",
            instruction="请生成一份汇报",
        )

        await service.publish_task_completed(
            "session-1",
            intent="ppt",
            message="AI PPT 任务已创建。",
            status="completed",
            artifact={
                "kind": "ppt",
                "job_id": "aippt-job-1",
                "download_url": "/api/v1/ppt/files/aippt-job-1",
            },
            messages=[
                {"role": "user", "content": "请生成一份汇报"},
                {"role": "assistant", "content": "AI PPT 任务已创建。"},
            ],
        )

        session = await service.get_session("session-1")
        assert session is not None
        assert session.intent == "ppt"
        assert session.artifact == {
            "kind": "ppt",
            "job_id": "aippt-job-1",
            "download_url": "/api/v1/ppt/files/aippt-job-1",
        }
        assert [
            {key: message.model_dump()[key] for key in ("role", "content", "timestamp")}
            for message in session.messages
        ] == [
            {"role": "user", "content": "请生成一份汇报", "timestamp": None},
            {"role": "assistant", "content": "AI PPT 任务已创建。", "timestamp": None},
        ]

    asyncio.run(run())


def test_list_sessions_omits_large_artifact_content_but_detail_keeps_it() -> None:
    manager = SyncConnectionManager()
    service = SyncService(manager=manager)

    async def run() -> None:
        await service.register_session(
            "session-1",
            source="feishu",
            title="测试会话",
            summary="文档完成",
            artifact={
                "kind": "docx",
                "content": "很长的文档正文" * 200,
                "sharing_url": "https://example.feishu.cn/docx/doc1",
            },
        )

        listed = await service.list_sessions()
        detail = await service.get_session("session-1")

        assert listed[0].artifact is not None
        assert "content" not in listed[0].artifact
        assert listed[0].artifact["content_length"] == len("很长的文档正文" * 200)
        assert listed[0].artifact["content_preview"].startswith("很长的文档正文")
        assert listed[0].artifact["sharing_url"] == "https://example.feishu.cn/docx/doc1"
        assert detail is not None
        assert detail.artifact is not None
        assert detail.artifact["content"] == "很长的文档正文" * 200

    asyncio.run(run())


def test_publish_agent_message_persists_when_websocket_send_hangs() -> None:
    manager = SyncConnectionManager()
    service = SyncService(manager=manager)

    class HangingWebSocket:
        async def send_json(self, envelope):  # type: ignore[no-untyped-def]
            await asyncio.sleep(5)

    async def run() -> None:
        await service.register_session(
            "session-1",
            source="feishu",
            title="测试会话",
            summary="测试摘要",
            messages=[{"role": "user", "content": "生成文学主题 ppt"}],
        )
        manager._connections["session-1"].add(HangingWebSocket())  # type: ignore[arg-type]

        await service.publish_agent_message(
            "session-1",
            role="assistant",
            content="整理展示目标并创建 AI PPT 任务。",
        )

        session = await service.get_session("session-1")
        assert session is not None
        assert session.summary == "整理展示目标并创建 AI PPT 任务。"
        assert [message.content for message in session.messages] == [
            "生成文学主题 ppt",
            "整理展示目标并创建 AI PPT 任务。",
        ]

    asyncio.run(run())


def test_get_session_refreshes_stale_memory_record_from_redis() -> None:
    manager = SyncConnectionManager()

    async def run() -> None:
        stale = await manager.register_session(
            "session-1",
            source="feishu",
            title="测试会话",
            summary="我判断这次要走 ppt 能力。",
            messages=[
                {"role": "user", "content": "生成时尚主题 ppt"},
                {"role": "assistant", "content": "我判断这次要走 ppt 能力。"},
            ],
        )
        fresh = SessionRecord(
            session_id=stale.session_id,
            source=stale.source,
            title=stale.title,
            summary="AI PPT 已生成。",
            status="completed",
            chat_id=stale.chat_id,
            message_id=stale.message_id,
            context_size=stale.context_size,
            instruction=stale.instruction,
            intent="ppt",
            artifact={"kind": "ppt", "status": "done"},
            context_messages=stale.context_messages,
            messages=[
                {"role": "user", "content": "生成时尚主题 ppt"},
                {"role": "assistant", "content": "我判断这次要走 ppt 能力。"},
                {"role": "assistant", "content": "AI PPT 已生成。"},
            ],
            opened_at=stale.opened_at,
            updated_at="9999-01-01T00:00:00+00:00",
        )

        async def load_from_redis(session_id: str):  # type: ignore[no-untyped-def]
            assert session_id == "session-1"
            return fresh

        manager._load_session_from_redis = load_from_redis  # type: ignore[method-assign]

        session = await manager.get_session("session-1")
        assert session is not None
        assert session.summary == "AI PPT 已生成。"
        assert session.intent == "ppt"
        assert session.artifact == {"kind": "ppt", "status": "done"}
        assert [message["content"] for message in session.messages or []] == [
            "生成时尚主题 ppt",
            "我判断这次要走 ppt 能力。",
            "AI PPT 已生成。",
        ]

    asyncio.run(run())
