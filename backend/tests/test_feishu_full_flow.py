from __future__ import annotations

from typing import Any
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from app.modules.agent.schemas import AgentChatRequest
from app.modules.feishu.events import FeishuEventProcessor
from app.modules.sync.manager import SyncConnectionManager
from app.modules.sync.service import SyncService

class _AgentServiceStub:
    def __init__(self) -> None:
        self.chat_requests: list[AgentChatRequest] = []

    async def chat(self, request: AgentChatRequest) -> None:
        self.chat_requests.append(request)

    async def chat_stream_events(self, request: AgentChatRequest):
        self.chat_requests.append(request)
        yield {
            "event": "result.created",
            "status": "completed",
            "channel": "artifact",
            "visibility": "user",
            "message": "飞书画板任务已完成。",
            "payload": {
                "response": {
                    "session_id": request.session_id,
                    "intent": "board",
                    "status": "completed",
                    "message": "飞书画板任务已完成。",
                    "artifact": {"kind": "board", "sharing_url": "https://example.feishu.cn/docx/doc_board"},
                }
            },
        }


class _FeishuServiceStub:
    def __init__(self) -> None:
        self.sent_messages: list[tuple[str, str]] = []
        self.created_boards: list[str] = []
        self.context_candidates = [
            {"role": "user", "content": "销售 A：华东 120 万", "timestamp": 1710000000001},
            {"role": "user", "content": "销售 B：华南 80 万", "timestamp": 1710000000002},
            {"role": "user", "content": "销售 C：华北 60 万", "timestamp": 1710000000003},
        ]
        self._client = None

    def get_bot_open_id(self) -> str:
        return "ou_bot"

    def get_chat_context_candidates(self, *_: object, **__: object) -> list[dict[str, object]]:
        return self.context_candidates

    async def send_text_message_to_chat(self, chat_id: str, text: str) -> dict[str, object]:
        self.sent_messages.append((chat_id, text))
        return {}

    async def create_board_document(self, title: str) -> dict[str, str]:
        self.created_boards.append(title)
        return {
            "document_id": "doc_board",
            "whiteboard_id": "wb_board",
            "sharing_url": "https://example.feishu.cn/docx/doc_board",
        }

    async def add_docx_permission_for_chat(self, *_: object, **__: object) -> dict[str, object]:
        return {}

    async def publish_markdown_to_feishu(self, *_: object, **__: object) -> dict[str, object]:
        return {"document_url": "https://example.feishu.cn/docx/doc_docx", "record_id": None}

    async def get_message(self, _message_id: str) -> None:
        return None


class _DocumentServiceStub:
    async def generate_document(self, _request: object) -> str:
        return "# Stub 文档\n\n内容生成成功。"

    async def generate_document_stream(self, _request: object):
        yield "# Stub 文档\n\n内容生成成功。"

    def ground_document_if_needed(self, _request: object, content: str) -> str:
        return content

    async def edit_document(self, request: object) -> str:
        return f"{getattr(request, 'current_content', '')}\n已编辑。"


class _AIPPTServiceStub:
    def create_job_from_request(self, _request: object) -> object:
        return type(
            "PPTJob",
            (),
            {
                "job_id": "job_stub",
                "status": "queued",
                "progress": 0,
                "current_step": "queued",
                "download_url": None,
                "error": None,
            },
        )()


class _CanvasServiceStub:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def create_board_task(self, request: object) -> object:
        self.requests.append(request)
        return type("BoardTask", (), {"task_id": "board_task_stub"})()

    def run_board_task(self, task_id: str) -> object:
        latest_request = self.requests[-1]
        return type(
            "CompletedBoardTask",
            (),
            {
                "task_id": task_id,
                "message": latest_request.message,
                "sharing_url": latest_request.sharing_url,
                "status": "succeeded",
                "current_step": "succeeded",
                "render_mode": "create_notes",
                "whiteboard_id": "wb_board",
                "preview_url": "https://example.feishu.cn/preview.png",
                "ticket_id": None,
                "node_ids": ["n1", "n2"],
                "deleted_count": 0,
                "logs": [],
                "result_summary": "board ok",
                "error_message": None,
            },
        )()


class _ProcessorForFullFlow(FeishuEventProcessor):
    def __init__(
        self,
        *,
        feishu_service: _FeishuServiceStub,
        agent_service: _AgentServiceStub,
        sync_service: SyncService,
    ) -> None:
        super().__init__(feishu_service=feishu_service, agent_service=agent_service, sync_service=sync_service)
        self.scheduled_bootstraps: list[dict[str, Any]] = []
        self.scheduled_agent_requests: list[AgentChatRequest] = []

    async def _resolve_sender_profile(self, _sender: Any) -> dict[str, Any]:
        return {"platform_user_id": "user_test", "sender_open_id": "ou_user"}

    def _schedule_new_session_bootstrap(self, **kwargs: Any) -> None:
        self.scheduled_bootstraps.append(kwargs)

    def _schedule_agent_chat(self, request: AgentChatRequest) -> None:
        self.scheduled_agent_requests.append(request)


def _mentioned_group_payload(text: str) -> dict[str, object]:
    return {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_user"}},
            "message": {
                "message_id": "om_full",
                "chat_id": "oc_full",
                "chat_type": "group",
                "create_time": "1710000000004",
                "content": f'{{"text": "{text}"}}',
                "mentions": [
                    {
                        "key": "@_user_1",
                        "id": "cli_app_test",
                        "id_type": "app_id",
                        "name": "Eko",
                    }
                ],
            },
        },
    }


class FeishuMentionContextSelectionFullFlowTest(IsolatedAsyncioTestCase):
    async def test_mentioned_board_request_bootstraps_context_then_runs_new_agent_route(self) -> None:
        sync_service = SyncService(SyncConnectionManager())
        feishu_service = _FeishuServiceStub()
        agent_service = _AgentServiceStub()
        processor = _ProcessorForFullFlow(
            feishu_service=feishu_service,
            agent_service=agent_service,
            sync_service=sync_service,
        )

        with patch("app.modules.feishu.events.settings.FEISHU_APP_ID", "cli_app_test"):
            result = await processor.handle(_mentioned_group_payload("@_user_1 根据聊天记录生成销售饼图画板"))

        session_id = "feishu:oc_full:om_full"
        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(len(feishu_service.sent_messages), 1)
        self.assertEqual(feishu_service.sent_messages[0][0], "oc_full")
        self.assertIn(f"http://127.0.0.1:3002/sessions/{session_id}", feishu_service.sent_messages[0][1])
        self.assertEqual(len(processor.scheduled_bootstraps), 1)

        opened_session = await sync_service.get_session(session_id)
        self.assertIsNotNone(opened_session)
        assert opened_session is not None
        self.assertEqual(opened_session.status, "进行中")
        self.assertIsNone(opened_session.intent)

        await processor._bootstrap_new_session(**processor.scheduled_bootstraps[0])

        loaded_session = await sync_service.get_session(session_id)
        self.assertIsNotNone(loaded_session)
        assert loaded_session is not None
        self.assertEqual(loaded_session.status, "进行中")
        self.assertEqual(loaded_session.context_size, 3)
        self.assertEqual([message.content for message in loaded_session.context_messages], [
            "销售 A：华东 120 万",
            "销售 B：华南 80 万",
            "销售 C：华北 60 万",
        ])
        self.assertEqual([message.content for message in loaded_session.selected_context_messages], [
            "销售 A：华东 120 万",
            "销售 B：华南 80 万",
            "销售 C：华北 60 万",
        ])
        self.assertEqual(agent_service.chat_requests, [])
        self.assertEqual(len(processor.scheduled_agent_requests), 1)
        request = processor.scheduled_agent_requests[0]
        self.assertEqual(request.session_id, session_id)
        self.assertEqual(request.message, "根据聊天记录生成销售饼图画板")
        self.assertIsNone(request.context)
