from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from app.modules.feishu.events import FeishuEventProcessor


class _SyncServiceStub:
    def __init__(self) -> None:
        self.opened_sessions: list[str] = []
        self.agent_messages: list[tuple[str, str]] = []
        self.context_updates: list[dict[str, object]] = []

    async def publish_session_opened(self, session_id: str, **_: object) -> None:
        self.opened_sessions.append(session_id)

    async def publish_agent_message(self, session_id: str, *, content: str, **_: object) -> None:
        self.agent_messages.append((session_id, content))

    async def update_session_context(self, session_id: str, **kwargs: object) -> None:
        self.context_updates.append({"session_id": session_id, **kwargs})


class _FeishuServiceStub:
    def get_bot_open_id(self) -> str:
        return "ou_bot"

    def get_chat_context_candidates(self, *_: object, **__: object) -> list[dict[str, object]]:
        return [{"role": "user", "content": "会议记录 1", "timestamp": 1}]


class _ProcessorForTest(FeishuEventProcessor):
    def __init__(self) -> None:
        self.sync = _SyncServiceStub()
        super().__init__(feishu_service=_FeishuServiceStub(), agent_service=object(), sync_service=self.sync)
        self.scheduled_sessions: list[str] = []

    def _schedule_new_session_bootstrap(self, *, session_id: str, **_: object) -> None:
        self.scheduled_sessions.append(session_id)


class _ProcessorBootstrapForTest(_ProcessorForTest):
    async def _run_agent_stream_to_session(self, request):  # noqa: ANN001
        raise AssertionError("agent should not run before context selection")


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

    async def test_bootstrap_loads_context_and_waits_for_selection(self) -> None:
        processor = _ProcessorBootstrapForTest()

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
        self.assertEqual(update["status"], "等待选择")
