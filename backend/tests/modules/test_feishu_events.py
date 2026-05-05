from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.agent.dependencies import get_agent_service
from app.modules.agent.schemas import AgentChatResponse
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.events import FeishuEventProcessor
from app.modules.feishu.router import router as feishu_router
from app.modules.feishu.service import FeishuService
from app.modules.sync.dependencies import get_sync_service


class RecordingFeishuClient:
    def __init__(self, messages: list[dict[str, object]]) -> None:
        self.messages = messages
        self.calls: list[tuple[str, int | None, int]] = []

    def list_recent_chat_messages(
        self,
        chat_id: str,
        *,
        before_time_ms: int | None = None,
        lookback_minutes: int = 120,
        page_size: int | None = None,
        max_pages: int | None = None,
    ) -> list[dict[str, object]]:
        self.calls.append((chat_id, before_time_ms, lookback_minutes))
        _ = (page_size, max_pages)
        return self.messages


class RecordingSendFeishuClient(RecordingFeishuClient):
    def __init__(self) -> None:
        super().__init__([])
        self.sent_messages: list[tuple[str, str]] = []

    def send_text_message_to_chat(self, chat_id: str, text: str) -> dict[str, str]:
        self.sent_messages.append((chat_id, text))
        return {"message_id": "message-1"}


class FailingRecentMessagesFeishuClient(RecordingFeishuClient):
    def list_recent_chat_messages(
        self,
        chat_id: str,
        *,
        before_time_ms: int | None = None,
        lookback_minutes: int = 120,
        page_size: int | None = None,
        max_pages: int | None = None,
    ) -> list[dict[str, object]]:
        self.calls.append((chat_id, before_time_ms, lookback_minutes))
        _ = (page_size, max_pages)
        raise RuntimeError("invalid container_id")


class RecordingAgentService:
    def __init__(self, sync_service: RecordingSyncService | None = None) -> None:
        self.requests: list[object] = []
        self._sync_service = sync_service

    async def chat(self, request):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        response = AgentChatResponse(
            session_id=request.session_id,
            intent="chat",
            status="completed",
            message="processed",
        )
        if self._sync_service is not None:
            await self._sync_service.publish_task_completed(
                request.session_id,
                intent=response.intent,
                message=response.message,
                status=response.status,
                artifact=None,
                error=None,
            )
        return response

    async def chat_stream_events(self, request):  # type: ignore[no-untyped-def]
        yield {"event": "turn.started", "message": "收到。我先理解你的任务，并拆成可以执行的步骤。"}
        yield {"event": "intent.recognized", "message": "我判断这次要走 ppt 能力。"}
        yield {"event": "tool.started", "message": "好的，我现在调用 ppt 能力。"}
        response = await self.chat(request)
        yield {"event": "result.created", "payload": {"response": response.model_dump()}, "message": response.message}


class FailingStreamAgentService(RecordingAgentService):
    async def chat_stream_events(self, request):  # type: ignore[no-untyped-def]
        yield {"event": "turn.started", "message": "收到。我先理解你的任务，并拆成可以执行的步骤。"}
        raise RuntimeError("boom")


class RecordingSyncService:
    def __init__(self) -> None:
        self.opened: list[dict[str, object]] = []
        self.context_updates: list[dict[str, object]] = []
        self.completed: list[dict[str, object]] = []
        self.errors: list[dict[str, object]] = []
        self.sessions: dict[str, dict[str, object]] = {}

    async def publish_session_opened(
        self,
        session_id: str,
        *,
        source: str,
        chat_id: str | None = None,
        message_id: str | None = None,
        context_size: int | None = None,
        instruction: str | None = None,
        context_messages: list[dict[str, object]] | None = None,
        messages: list[dict[str, object]] | None = None,
    ) -> None:
        self.opened.append(
            {
                "session_id": session_id,
                "source": source,
                "chat_id": chat_id,
                "message_id": message_id,
                "context_size": context_size,
            }
        )
        self.sessions[session_id] = {
            "session_id": session_id,
            "source": source,
            "chat_id": chat_id,
            "message_id": message_id,
            "context_size": context_size,
            "instruction": instruction,
            "context_messages": context_messages or [],
            "messages": messages or [],
        }

    async def get_session(self, session_id: str):  # type: ignore[no-untyped-def]
        return self.sessions.get(session_id)

    async def list_sessions(self):  # type: ignore[no-untyped-def]
        class Session:
            def __init__(self, data):  # type: ignore[no-untyped-def]
                self.session_id = data.get("session_id")
                self.chat_id = data.get("chat_id")
                self.artifact = data.get("artifact")
                self.updated_at = data.get("updated_at") or ""

        return [Session(data) for data in self.sessions.values()]

    async def update_session_context(
        self,
        session_id: str,
        *,
        context_size: int,
        context_messages: list[dict[str, object]],
    ) -> None:
        self.context_updates.append(
            {
                "session_id": session_id,
                "context_size": context_size,
                "context_messages": context_messages,
            }
        )
        if session_id in self.sessions:
            self.sessions[session_id]["context_size"] = context_size
            self.sessions[session_id]["context_messages"] = context_messages

    async def publish_task_completed(
        self,
        session_id: str,
        *,
        intent: str,
        message: str,
        status: str,
        artifact: dict[str, object] | None = None,
        messages: list[dict[str, object]] | None = None,
        error: str | None = None,
    ) -> None:
        self.completed.append(
            {
                "session_id": session_id,
                "intent": intent,
                "message": message,
                "status": status,
                "artifact": artifact,
                "error": error,
            }
        )
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = status
            self.sessions[session_id]["summary"] = message
            if messages is not None:
                self.sessions[session_id]["messages"] = messages

    async def publish_agent_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        replace_last: bool = False,
    ) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].setdefault("messages", [])
            messages = self.sessions[session_id]["messages"]  # type: ignore[index]
            if messages and messages[-1].get("role") == role and messages[-1].get("content") == content:  # type: ignore[union-attr]
                return
            if replace_last and messages and messages[-1].get("role") == role:  # type: ignore[union-attr]
                messages[-1] = {"role": role, "content": content}  # type: ignore[index]
            else:
                messages.append({"role": role, "content": content})  # type: ignore[union-attr]

    async def publish_error(self, session_id: str, message: str, error: str | None = None) -> None:
        self.errors.append(
            {
                "session_id": session_id,
                "message": message,
                "error": error,
            }
        )
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "failed"
            self.sessions[session_id]["summary"] = message


def _build_client(
    feishu_service: FeishuService,
    agent_service: RecordingAgentService,
    sync_service: RecordingSyncService | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(feishu_router, prefix="/api/v1/feishu")
    app.dependency_overrides[get_feishu_service] = lambda: feishu_service
    app.dependency_overrides[get_agent_service] = lambda: agent_service
    if sync_service is not None:
        app.dependency_overrides[get_sync_service] = lambda: sync_service
    return TestClient(app)


def test_feishu_event_route_returns_challenge_verbatim() -> None:
    client = _build_client(FeishuService(client=RecordingFeishuClient([])), RecordingAgentService())

    response = client.post("/api/v1/feishu/events", json={"challenge": "challenge-123"})

    assert response.status_code == 200
    assert response.json() == {"challenge": "challenge-123"}


def test_feishu_client_recent_messages_uses_empty_stub_without_credentials(monkeypatch) -> None:
    client = FeishuClient()

    def fail_request(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("list_recent_chat_messages should not call Feishu without app credentials")

    monkeypatch.setattr(client, "_request_json", fail_request)

    assert client.list_recent_chat_messages("oc_no_creds") == []


def test_feishu_service_suppresses_auto_sync_chat_notification() -> None:
    client = RecordingSendFeishuClient()
    service = FeishuService(client=client)  # type: ignore[arg-type]

    result = asyncio.run(
        service.send_text_message_to_chat(
            "oc_123",
            "Eko 已自动同步飞书文档：\nhttps://example.feishu.cn/docx/doc_1",
        )
    )

    assert result == {"message_id": "suppressed-auto-sync-message"}
    assert client.sent_messages == []


def test_feishu_event_route_plain_mention_opens_new_session() -> None:
    trigger_time = 1_700_000_000_000
    raw_messages = [
        {
            "message_id": "msg-1",
            "create_time": trigger_time - 7_200_000,
            "chat_id": "oc_123",
            "msg_type": "text",
            "body": {"content": json.dumps({"text": "早些时候的旧话题"})},
            "sender": {"sender_type": "user", "id": "u-1"},
        },
        {
            "message_id": "msg-2",
            "create_time": trigger_time - 6_900_000,
            "chat_id": "oc_123",
            "msg_type": "text",
            "body": {"content": json.dumps({"text": "上一段讨论"})},
            "sender": {"sender_type": "user", "id": "u-2"},
        },
        {
            "message_id": "msg-3",
            "create_time": trigger_time - 60_000,
            "chat_id": "oc_123",
            "msg_type": "text",
            "body": {"content": json.dumps({"text": "最近的上下文"})},
            "sender": {"sender_type": "user", "id": "u-3"},
        },
    ]
    feishu_service = FeishuService(client=RecordingFeishuClient(raw_messages))
    sync_service = RecordingSyncService()
    agent_service = RecordingAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_123"},
                    "sender_type": "user",
                },
                "message": {
                    "message_id": "msg-trigger",
                    "create_time": trigger_time,
                    "chat_id": "oc_123",
                    "thread_id": "thread-1",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "<at user_id=\"bot\"></at> 生成一份项目汇报 PPT"}),
                    "mentions": [{"id": "bot", "id_type": "app_id"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"msg": "success"}
    assert sync_service.opened == [
        {
            "session_id": "feishu:oc_123:msg-trigger",
            "source": "feishu",
            "chat_id": "oc_123",
            "message_id": "msg-trigger",
            "context_size": 0,
        }
    ]
    opened_messages = sync_service.sessions["feishu:oc_123:msg-trigger"]["messages"]
    assert opened_messages[0]["sender_open_id"] == "ou_123"
    assert len(opened_messages) == 2
    assert opened_messages[1]["content"] == "\n\n".join(
        [
            "收到。我先理解你的任务，并拆成可以执行的步骤。",
            "我判断这次要走 ppt 能力。",
            "好的，我现在调用 ppt 能力。",
            "processed",
        ]
    )
    assert feishu_service._client.calls == [("oc_123", trigger_time, 120)]  # type: ignore[attr-defined]
    assert sync_service.context_updates[0]["session_id"] == "feishu:oc_123:msg-trigger"
    assert sync_service.context_updates[0]["context_size"] == 3
    assert sync_service.context_updates[0]["context_messages"][0]["sender_open_id"] == "u-1"
    assert len(agent_service.requests) == 1
    assert agent_service.requests[0].message == "生成一份项目汇报 PPT"
    assert agent_service.requests[0].sender["sender_open_id"] == "ou_123"


def test_feishu_event_context_fetch_failure_still_runs_agent_with_empty_context() -> None:
    trigger_time = 1_700_000_000_000
    feishu_service = FeishuService(client=FailingRecentMessagesFeishuClient([]))
    sync_service = RecordingSyncService()
    agent_service = RecordingAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_123"},
                    "sender_type": "user",
                },
                "message": {
                    "message_id": "msg-trigger",
                    "create_time": trigger_time,
                    "chat_id": "oc_bad",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "<at user_id=\"bot\"></at> 生成一份客户续费风险分析文档"}),
                    "mentions": [{"id": "bot", "id_type": "app_id"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"msg": "success"}
    assert feishu_service._client.calls == [("oc_bad", trigger_time, 120)]  # type: ignore[attr-defined]
    assert sync_service.context_updates == [
        {
            "session_id": "feishu:oc_bad:msg-trigger",
            "context_size": 0,
            "context_messages": [],
        }
    ]
    assert len(agent_service.requests) == 1
    assert agent_service.requests[0].message == "生成一份客户续费风险分析文档"
    assert agent_service.requests[0].context.chat_history == []


def test_feishu_event_strips_plain_mention_name_from_sdk_payload() -> None:
    feishu_service = FeishuService(client=RecordingFeishuClient([]))
    sync_service = RecordingSyncService()
    agent_service = RecordingAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_123"},
                    "sender_type": "user",
                },
                "message": {
                    "message_id": "msg-trigger",
                    "create_time": 1_700_000_000_000,
                    "chat_id": "oc_123",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "高天磊 生成文学主题 ppt"}),
                    "mentions": [{"key": "高天磊", "name": "Eko"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"msg": "success"}
    assert agent_service.requests[0].message == "生成文学主题 ppt"


def test_feishu_direct_mention_followup_uses_latest_chat_ppt_artifact() -> None:
    trigger_time = 1_700_000_000_000
    feishu_service = FeishuService(client=RecordingFeishuClient([]))
    sync_service = RecordingSyncService()
    sync_service.sessions["feishu:oc_123:old-ppt"] = {
        "session_id": "feishu:oc_123:old-ppt",
        "source": "feishu",
        "chat_id": "oc_123",
        "message_id": "old-ppt",
        "context_size": 0,
        "instruction": "生成环保主题 PPT",
        "context_messages": [],
        "messages": [],
        "artifact": {
            "kind": "ppt",
            "job_id": "aippt-old",
            "status": "done",
            "download_url": "/api/v1/ppt/files/aippt-old",
        },
    }
    agent_service = RecordingAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_123"},
                    "sender_type": "user",
                },
                "message": {
                    "message_id": "msg-followup",
                    "create_time": trigger_time,
                    "chat_id": "oc_123",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "<at user_id=\"bot\"></at> 把第一页改得更商务一点"}),
                    "mentions": [{"id": "bot", "id_type": "app_id"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert len(agent_service.requests) == 1
    request = agent_service.requests[0]
    assert request.current_document is not None
    assert request.current_document.kind == "ppt"
    assert request.current_document.job_id == "aippt-old"


def test_feishu_direct_mention_followup_skips_failed_ppt_artifact() -> None:
    trigger_time = 1_700_000_000_000
    feishu_service = FeishuService(client=RecordingFeishuClient([]))
    sync_service = RecordingSyncService()
    sync_service.sessions["feishu:oc_123:failed-ppt"] = {
        "session_id": "feishu:oc_123:failed-ppt",
        "source": "feishu",
        "chat_id": "oc_123",
        "message_id": "failed-ppt",
        "context_size": 0,
        "instruction": "修改环保主题 PPT",
        "context_messages": [],
        "messages": [],
        "artifact": {
            "kind": "ppt",
            "job_id": "aippt-failed",
            "status": "failed",
            "download_url": None,
        },
    }
    sync_service.sessions["feishu:oc_123:old-ppt"] = {
        "session_id": "feishu:oc_123:old-ppt",
        "source": "feishu",
        "chat_id": "oc_123",
        "message_id": "old-ppt",
        "context_size": 0,
        "instruction": "生成环保主题 PPT",
        "context_messages": [],
        "messages": [],
        "artifact": {
            "kind": "ppt",
            "job_id": "aippt-old",
            "status": "done",
            "download_url": "/api/v1/ppt/files/aippt-old",
        },
    }
    agent_service = RecordingAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_123"},
                    "sender_type": "user",
                },
                "message": {
                    "message_id": "msg-followup",
                    "create_time": trigger_time,
                    "chat_id": "oc_123",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "<at user_id=\"bot\"></at> 把第2页标题改成「高频问题」"}),
                    "mentions": [{"id": "bot", "id_type": "app_id"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert len(agent_service.requests) == 1
    request = agent_service.requests[0]
    assert request.current_document is not None
    assert request.current_document.job_id == "aippt-old"


def test_feishu_event_opens_session_before_sender_resolution() -> None:
    order: list[str] = []
    feishu_service = FeishuService(client=RecordingFeishuClient([]))
    sync_service = RecordingSyncService()
    agent_service = RecordingAgentService(sync_service)
    processor = FeishuEventProcessor(feishu_service, agent_service, sync_service)

    async def slow_sender_resolution(sender):  # type: ignore[no-untyped-def]
        order.append("resolve_sender")
        await asyncio.sleep(0)
        return {"sender_open_id": "ou_slow"}

    async def recording_publish_session_opened(*args, **kwargs):  # type: ignore[no-untyped-def]
        order.append("open_session")
        await RecordingSyncService.publish_session_opened(sync_service, *args, **kwargs)

    processor._resolve_sender_profile = slow_sender_resolution  # type: ignore[method-assign]
    sync_service.publish_session_opened = recording_publish_session_opened  # type: ignore[method-assign]

    response = asyncio.run(
        processor.handle(
            {
                "schema": "2.0",
                "header": {
                    "event_type": "im.message.receive_v1",
                    "token": "",
                },
                "event": {
                    "sender": {
                        "sender_id": {"open_id": "ou_fast"},
                        "sender_type": "user",
                    },
                    "message": {
                        "message_id": "msg-trigger",
                        "create_time": 1_700_000_000_000,
                        "chat_id": "oc_123",
                        "chat_type": "group",
                        "message_type": "text",
                        "content": json.dumps({"text": "<at user_id=\"bot\"></at> 生成文档"}),
                        "mentions": [{"id": "bot", "id_type": "app_id"}],
                    },
                },
            }
        )
    )

    assert response == {"msg": "success"}
    assert order[0] == "open_session"
    opened_messages = sync_service.sessions["feishu:oc_123:msg-trigger"]["messages"]
    assert opened_messages[0]["sender_open_id"] == "ou_fast"


def test_feishu_event_stream_failure_is_visible_in_session() -> None:
    feishu_service = FeishuService(client=RecordingFeishuClient([]))
    sync_service = RecordingSyncService()
    agent_service = FailingStreamAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)
    asyncio.run(
        sync_service.publish_session_opened(
            "session-abc",
            source="feishu",
            chat_id="oc_123",
            message_id="msg-opened",
            context_size=0,
        )
    )

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "message": {
                    "message_id": "msg-chat",
                    "create_time": 1_700_000_000_000,
                    "chat_id": "oc_123",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "<at user_id=\"bot\"></at> /chat session-abc 生成体育主题 ppt"}),
                    "mentions": [{"id": "bot", "id_type": "app_id"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"msg": "success"}
    messages = sync_service.sessions["session-abc"]["messages"]
    assert [message["content"] for message in messages] == [
        "收到。我先理解你的任务，并拆成可以执行的步骤。",
        "执行失败：boom",
    ]


def test_feishu_event_route_new_command_is_no_longer_supported() -> None:
    trigger_time = 1_700_000_000_000
    feishu_service = FeishuService(
        client=RecordingFeishuClient(
            [
                {
                    "message_id": "msg-1",
                    "create_time": trigger_time - 60_000,
                    "chat_id": "oc_123",
                    "msg_type": "text",
                    "body": {"content": json.dumps({"text": "最近的上下文"})},
                    "sender": {"sender_type": "user", "id": "u-1"},
                }
            ]
        )
    )
    sync_service = RecordingSyncService()
    agent_service = RecordingAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "message": {
                    "message_id": "msg-new",
                    "create_time": trigger_time,
                    "chat_id": "oc_123",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "<at user_id=\"bot\"></at> /new 消息 xxxxxx"}),
                    "mentions": [{"id": "bot", "id_type": "app_id"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"msg": "success"}
    assert feishu_service._client.calls == []  # type: ignore[attr-defined]
    assert sync_service.opened == []
    assert sync_service.context_updates == []
    assert agent_service.requests == []
    assert sync_service.completed == []


def test_feishu_event_route_chat_command_requires_existing_session() -> None:
    feishu_service = FeishuService(client=RecordingFeishuClient([]))
    sync_service = RecordingSyncService()
    agent_service = RecordingAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "message": {
                    "message_id": "msg-chat",
                    "create_time": 1_700_000_000_000,
                    "chat_id": "oc_123",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "<at user_id=\"bot\"></at> /chat session-missing 你好"}),
                    "mentions": [{"id": "bot", "id_type": "app_id"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"msg": "success"}
    assert agent_service.requests == []
    assert feishu_service._client.calls == []  # type: ignore[attr-defined]
    assert sync_service.errors == [
        {
            "session_id": "session-missing",
            "message": "会话不存在，无法继续对话。",
            "error": "session not found",
        }
    ]


def test_feishu_event_route_chat_command_sends_message_to_existing_session() -> None:
    feishu_service = FeishuService(client=RecordingFeishuClient([]))
    sync_service = RecordingSyncService()
    agent_service = RecordingAgentService(sync_service)
    client = _build_client(feishu_service, agent_service, sync_service)

    asyncio.run(
        sync_service.publish_session_opened(
            "session-abc",
            source="feishu",
            chat_id="oc_123",
            message_id="msg-opened",
            context_size=0,
        )
    )

    response = client.post(
        "/api/v1/feishu/events",
        json={
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "",
            },
            "event": {
                "message": {
                    "message_id": "msg-chat",
                    "create_time": 1_700_000_000_000,
                    "chat_id": "oc_123",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "<at user_id=\"bot\"></at> /chat session-abc 继续聊一下"}),
                    "mentions": [{"id": "bot", "id_type": "app_id"}],
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"msg": "success"}
    assert feishu_service._client.calls == []  # type: ignore[attr-defined]
    assert len(agent_service.requests) == 1
    request = agent_service.requests[0]
    assert request.session_id == "session-abc"
    assert request.message == "继续聊一下"
    messages = sync_service.sessions["session-abc"]["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "\n\n".join(
        [
            "收到。我先理解你的任务，并拆成可以执行的步骤。",
            "我判断这次要走 ppt 能力。",
            "好的，我现在调用 ppt 能力。",
            "processed",
        ]
    )
