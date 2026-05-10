from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from app.modules.sync.manager import SyncConnectionManager
from app.modules.sync.service import SyncService


class SyncContextSelectionTest(IsolatedAsyncioTestCase):
    async def test_mark_session_running_preserves_candidates_and_persists_selected_context_messages(self) -> None:
        manager = SyncConnectionManager()
        service = SyncService(manager)
        candidates = [
            {"role": "user", "content": "不要纳入的早期消息", "timestamp": 1},
            {"role": "user", "content": "选中的会议记录 A", "timestamp": 2},
            {"role": "user", "content": "选中的会议记录 B", "timestamp": 3},
        ]
        await service.register_session(
            "feishu:oc_test:om_test",
            source="feishu",
            title="飞书群聊新会话",
            summary="等待选择上下文",
            status="等待选择",
            context_size=len(candidates),
            context_messages=candidates,
            instruction="根据聊天记录生成会议总结文档",
        )

        await service.mark_session_running(
            "feishu:oc_test:om_test",
            context_size=2,
            selected_context_messages=candidates[1:],
        )

        session = await service.get_session("feishu:oc_test:om_test")

        self.assertIsNotNone(session)
        self.assertEqual(session.context_size, 2)
        self.assertEqual([message.content for message in session.context_messages], [
            "不要纳入的早期消息",
            "选中的会议记录 A",
            "选中的会议记录 B",
        ])
        self.assertEqual([message.content for message in session.selected_context_messages], ["选中的会议记录 A", "选中的会议记录 B"])

    async def test_mark_session_running_can_skip_context_messages(self) -> None:
        manager = SyncConnectionManager()
        service = SyncService(manager)
        candidates = [
            {"role": "user", "content": "候选消息 1", "timestamp": 1},
            {"role": "user", "content": "候选消息 2", "timestamp": 2},
        ]
        await service.register_session(
            "feishu:oc_skip:om_skip",
            source="feishu",
            title="飞书群聊新会话",
            summary="等待选择上下文",
            status="等待选择",
            context_size=len(candidates),
            context_messages=candidates,
            instruction="直接生成文档",
        )

        await service.mark_session_running(
            "feishu:oc_skip:om_skip",
            context_size=0,
            selected_context_messages=[],
        )

        session = await service.get_session("feishu:oc_skip:om_skip")

        self.assertIsNotNone(session)
        self.assertEqual(session.context_size, 0)
        self.assertEqual([message.content for message in session.context_messages], ["候选消息 1", "候选消息 2"])
        self.assertEqual(session.selected_context_messages, [])
