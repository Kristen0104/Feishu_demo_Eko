from __future__ import annotations

from unittest import TestCase

from app.modules.feishu.service import FeishuService


class _FeishuClientContextStub:
    def __init__(self, messages: list[dict[str, object]]) -> None:
        self.messages = messages
        self.calls: list[dict[str, object]] = []

    def list_recent_chat_messages(self, chat_id: str, **kwargs: object) -> list[dict[str, object]]:
        self.calls.append({"chat_id": chat_id, **kwargs})
        return self.messages


def _message(index: int, *, content: str | None = None, create_time: int | None = None) -> dict[str, object]:
    return {
        "create_time": str(create_time if create_time is not None else 1_710_000_000_000 + index),
        "content": f'{{"text":"{content or f"消息 {index}"}"}}',
        "sender": {"sender_type": "user"},
    }


class FeishuContextCandidatesTest(TestCase):
    def test_candidates_are_latest_valid_messages_after_filtering(self) -> None:
        messages = [
            _message(1, content="早期消息 1"),
            {"create_time": "bad", "content": '{"text":"无效时间"}', "sender": {"sender_type": "user"}},
            _message(2, content="早期消息 2"),
            *[_message(index) for index in range(3, 23)],
            _message(23, content="触发机器人的这条不应进入", create_time=1_710_000_000_100),
        ]
        client = _FeishuClientContextStub(messages)
        service = FeishuService(client=client)

        candidates = service.get_chat_context_candidates(
            "oc_test",
            before_time_ms=1_710_000_000_100,
            limit=15,
        )

        self.assertEqual(len(candidates), 15)
        self.assertEqual(candidates[0]["content"], "消息 8")
        self.assertEqual(candidates[-1]["content"], "消息 22")
        self.assertNotIn("触发机器人的这条不应进入", [item["content"] for item in candidates])
        self.assertEqual(client.calls[0]["page_size"], 50)
        self.assertEqual(client.calls[0]["max_pages"], 3)
