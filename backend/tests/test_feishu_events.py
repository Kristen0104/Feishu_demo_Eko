from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from app.modules.agent.schemas import AgentIntent
from app.modules.feishu.events import FeishuEventProcessor


class _SyncServiceStub:
    def __init__(self) -> None:
        self.opened_sessions: list[str] = []
        self.opened_payloads: list[dict[str, object]] = []
        self.agent_messages: list[tuple[str, str]] = []
        self.context_updates: list[dict[str, object]] = []

    async def publish_session_opened(self, session_id: str, **kwargs: object) -> None:
        self.opened_sessions.append(session_id)
        self.opened_payloads.append({"session_id": session_id, **kwargs})

    async def publish_agent_message(self, session_id: str, *, content: str, **_: object) -> None:
        self.agent_messages.append((session_id, content))

    async def update_session_context(self, session_id: str, **kwargs: object) -> None:
        self.context_updates.append({"session_id": session_id, **kwargs})


class _FeishuServiceStub:
    def __init__(self) -> None:
        self.sent_messages: list[tuple[str, str]] = []

    def get_bot_open_id(self) -> str:
        return "ou_bot"

    def get_chat_context_candidates(self, *_: object, **__: object) -> list[dict[str, object]]:
        return [{"role": "user", "content": "会议记录 1", "timestamp": 1}]

    async def send_text_message_to_chat(self, chat_id: str, text: str) -> None:
        self.sent_messages.append((chat_id, text))


class _AgentServiceStub:
    def __init__(self, intent: AgentIntent = AgentIntent.DOCX) -> None:
        self.intent = intent


class _ProcessorForTest(FeishuEventProcessor):
    def __init__(self, intent: AgentIntent = AgentIntent.DOCX, *, dedupe_events: bool = False) -> None:
        self.sync = _SyncServiceStub()
        self.agent_service = _AgentServiceStub(intent)
        self.feishu = _FeishuServiceStub()
        super().__init__(
            feishu_service=self.feishu,
            agent_service=self.agent_service,
            sync_service=self.sync,
            dedupe_events=dedupe_events,
        )
        self.scheduled_sessions: list[str] = []
        self.scheduled_chat_requests: list[object] = []

    def _schedule_new_session_bootstrap(self, *, session_id: str, **_: object) -> None:
        self.scheduled_sessions.append(session_id)

    def _schedule_agent_chat(self, request):  # noqa: ANN001
        self.scheduled_chat_requests.append(request)


def _payload(*, text: str, chat_type: str, mentions: list[dict[str, object]] | None = None) -> dict[str, object]:
    message: dict[str, object] = {
        "message_id": "om_test",
        "chat_id": "oc_test",
        "chat_type": chat_type,
        "create_time": "1710000000000",
        "content": f'{{"text": "{text}"}}',
    }
    if mentions is not None:
        message["mentions"] = mentions
    return {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_user"}},
            "message": message,
        },
    }


class FeishuEventProcessorMentionGateTest(IsolatedAsyncioTestCase):
    async def test_configured_verification_token_is_required(self) -> None:
        processor = _ProcessorForTest()

        with patch("app.modules.feishu.events.settings.FEISHU_VERIFICATION_TOKEN", "expected_token"):
            with self.assertRaises(ValueError):
                await processor.handle(_payload(text="帮我写个周报", chat_type="p2p"))

    async def test_duplicate_message_id_is_ignored_when_dedupe_enabled(self) -> None:
        processor = _ProcessorForTest(dedupe_events=True)

        first = await processor.handle(_payload(text="帮我写个周报", chat_type="p2p"))
        second = await processor.handle(_payload(text="帮我写个周报", chat_type="p2p"))

        self.assertEqual(first, {"msg": "success"})
        self.assertEqual(second, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])

    async def test_group_message_without_mention_is_ignored(self) -> None:
        processor = _ProcessorForTest()

        result = await processor.handle(_payload(text="帮我写个周报", chat_type="group"))

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, [])
        self.assertEqual(processor.scheduled_sessions, [])

    async def test_group_message_with_bot_mention_opens_session(self) -> None:
        processor = _ProcessorForTest()

        with patch("app.modules.feishu.events.settings.FEISHU_APP_ID", "cli_app_test"):
            result = await processor.handle(
                _payload(
                    text="@_user_1 帮我写个周报",
                    chat_type="group",
                    mentions=[{"key": "@_user_1", "id": "cli_app_test", "id_type": "app_id", "name": "Eko"}],
                )
            )

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(len(processor.feishu.sent_messages), 1)
        self.assertIn("http://127.0.0.1:3002/sessions/feishu:oc_test:om_test", processor.feishu.sent_messages[0][1])

    async def test_group_message_with_long_connection_bot_mention_opens_session(self) -> None:
        processor = _ProcessorForTest()

        with patch("app.modules.feishu.events.settings.FEISHU_APP_ID", "cli_app_test"):
            result = await processor.handle(
                _payload(
                    text="@_user_1 帮我写个周报",
                    chat_type="group",
                    mentions=[
                        {
                            "key": "@_user_1",
                            "id": {"open_id": "ou_bot", "union_id": "on_bot", "user_id": ""},
                            "mentioned_type": "bot",
                            "name": "Eko",
                        }
                    ],
                )
            )

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])

    async def test_group_message_with_plain_text_bot_name_opens_session(self) -> None:
        processor = _ProcessorForTest()

        with patch("app.modules.feishu.events.settings.FEISHU_APP_ID", "cli_app_test"):
            with patch.object(__import__("app.modules.feishu.events", fromlist=["settings"]).settings, "FEISHU_BOT_NAME", "Eko_Test", create=True):
                result = await processor.handle(
                    _payload(
                        text="@Eko_Test 根据聊天记录生成预算饼图",
                        chat_type="group",
                        mentions=[],
                    )
                )

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])

    async def test_group_message_mentioning_someone_else_is_ignored(self) -> None:
        processor = _ProcessorForTest()

        with patch("app.modules.feishu.events.settings.FEISHU_APP_ID", "cli_app_test"):
            result = await processor.handle(
                _payload(
                    text="@_user_1 帮我写个周报",
                    chat_type="group",
                    mentions=[{"key": "@_user_1", "id": "ou_other", "id_type": "open_id", "name": "别人"}],
                )
            )

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, [])
        self.assertEqual(processor.scheduled_sessions, [])

    async def test_group_message_with_unreferenced_bot_mention_is_ignored(self) -> None:
        processor = _ProcessorForTest()

        with patch("app.modules.feishu.events.settings.FEISHU_APP_ID", "cli_app_test"):
            result = await processor.handle(
                _payload(
                    text="@_user_2 帮我写个周报",
                    chat_type="group",
                    mentions=[
                        {"key": "@_user_1", "id": "cli_app_test", "id_type": "app_id", "name": "Eko"},
                        {"key": "@_user_2", "id": "ou_other", "id_type": "open_id", "name": "别人"},
                    ],
                )
            )

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])

    async def test_private_chat_without_mention_opens_session(self) -> None:
        processor = _ProcessorForTest()

        result = await processor.handle(_payload(text="帮我写个周报", chat_type="p2p"))

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(len(processor.feishu.sent_messages), 1)
        self.assertIn("工作台链接", processor.feishu.sent_messages[0][1])
        self.assertIn("http://127.0.0.1:3002/sessions/feishu:oc_test:om_test", processor.feishu.sent_messages[0][1])

    async def test_vague_organize_request_uses_normal_agent_bootstrap(self) -> None:
        processor = _ProcessorForTest()

        with patch("app.modules.feishu.events.settings.FEISHU_APP_ID", "cli_app_test"):
            result = await processor.handle(_payload(text="@_user_1 整理一下", chat_type="group", mentions=[{"key": "@_user_1", "id": "cli_app_test", "id_type": "app_id", "name": "Eko"}]))

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_chat_requests, [])
        self.assertEqual(processor.sync.agent_messages, [("feishu:oc_test:om_test", "收到。我先读取群聊上下文，并继续处理。")])
        self.assertEqual(processor.sync.context_updates, [])
        self.assertEqual(len(processor.feishu.sent_messages), 1)
        self.assertIn("http://127.0.0.1:3002/sessions/feishu:oc_test:om_test", processor.feishu.sent_messages[0][1])
        opened = processor.sync.opened_payloads[0]
        self.assertEqual(opened["status"], "进行中")
        self.assertEqual(opened["context_size"], 0)
        self.assertNotIn("route_state", opened)

    async def test_vague_organize_request_with_modal_particle_uses_normal_agent_bootstrap(self) -> None:
        for text, original_message in (
            ("@_user_1 整理一下吧", "整理一下吧"),
            ("@_user_1 帮我整理一下吧", "帮我整理一下吧"),
            ("@_user_1 整理下吧", "整理下吧"),
        ):
            processor = _ProcessorForTest()

            with patch("app.modules.feishu.events.settings.FEISHU_APP_ID", "cli_app_test"):
                result = await processor.handle(
                    _payload(
                        text=text,
                        chat_type="group",
                        mentions=[{"key": "@_user_1", "id": "cli_app_test", "id_type": "app_id", "name": "Eko"}],
                    )
                )

            self.assertEqual(result, {"msg": "success"})
            self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
            self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])
            self.assertEqual(processor.scheduled_chat_requests, [])
            self.assertEqual(processor.sync.opened_payloads[0]["instruction"], original_message)
            self.assertNotIn("route_state", processor.sync.opened_payloads[0])
            self.assertEqual(len(processor.feishu.sent_messages), 1)

    async def test_direct_message_uses_same_bootstrap_without_feishu_prerouting(self) -> None:
        processor = _ProcessorForTest(intent=AgentIntent.CHAT)

        result = await processor.handle(_payload(text="NovaMind 模型分级策略", chat_type="p2p"))

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(len(processor.feishu.sent_messages), 1)
        self.assertIn("http://127.0.0.1:3002/sessions/feishu:oc_test:om_test", processor.feishu.sent_messages[0][1])
        opened = processor.sync.opened_payloads[0]
        self.assertNotIn("intent", opened)
        self.assertEqual(opened["context_size"], 0)

    async def test_board_chart_request_runs_immediately_without_context_selection(self) -> None:
        processor = _ProcessorForTest(intent=AgentIntent.BOARD)

        result = await processor.handle(_payload(text="生成销售饼图", chat_type="p2p"))

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(len(processor.feishu.sent_messages), 1)
        self.assertIn("http://127.0.0.1:3002/sessions/feishu:oc_test:om_test", processor.feishu.sent_messages[0][1])
        self.assertEqual(processor.sync.agent_messages, [("feishu:oc_test:om_test", "收到。我先读取群聊上下文，并继续处理。")])

    async def test_board_chart_request_with_chat_history_uses_new_route(self) -> None:
        processor = _ProcessorForTest(intent=AgentIntent.BOARD)

        result = await processor.handle(_payload(text="根据聊天记录生成销售饼图", chat_type="p2p"))

        self.assertEqual(result, {"msg": "success"})
        self.assertEqual(processor.sync.opened_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.scheduled_sessions, ["feishu:oc_test:om_test"])
        self.assertEqual(processor.sync.agent_messages, [("feishu:oc_test:om_test", "收到。我先读取群聊上下文，并继续处理。")])
        self.assertEqual(len(processor.feishu.sent_messages), 1)
        self.assertEqual(processor.feishu.sent_messages[0][0], "oc_test")
        self.assertIn("http://127.0.0.1:3002/sessions/feishu:oc_test:om_test", processor.feishu.sent_messages[0][1])

    async def test_bootstrap_loads_context_and_continues_agent_chat(self) -> None:
        processor = _ProcessorForTest(intent=AgentIntent.BOARD)
        await processor._bootstrap_new_session(
            session_id="feishu:oc_test:om_test",
            chat_id="oc_test",
            before_time_ms=123,
            instruction="生成文档",
            sender_profile=None,
        )

        self.assertEqual(len(processor.sync.context_updates), 1)
        update = processor.sync.context_updates[0]
        self.assertEqual(update["session_id"], "feishu:oc_test:om_test")
        self.assertEqual(update["context_size"], 1)
        self.assertEqual(update["status"], "进行中")
        self.assertEqual(update["selected_context_messages"], [{"role": "user", "content": "会议记录 1", "timestamp": 1}])
        self.assertEqual(len(processor.scheduled_chat_requests), 1)
        self.assertIsNone(processor.scheduled_chat_requests[0].context)

    async def test_bootstrap_runs_agent_chat_even_when_session_was_waiting_selection(self) -> None:
        processor = _ProcessorForTest(intent=AgentIntent.BOARD)

        class _WaitingSession:
            status = "等待选择"

        async def _get_session(_: str) -> object:
            return _WaitingSession()

        processor.sync.get_session = _get_session  # type: ignore[assignment]

        await processor._bootstrap_new_session(
            session_id="feishu:oc_test:om_test",
            chat_id="oc_test",
            before_time_ms=123,
            instruction="根据上下文生成预算饼图",
            sender_profile=None,
        )

        self.assertEqual(len(processor.scheduled_chat_requests), 1)
