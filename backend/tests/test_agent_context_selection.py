from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from app.modules.agent.context import AgentContextAssembler
from app.modules.agent.schemas import AgentChatRequest
from app.modules.sync.manager import SyncConnectionManager
from app.modules.sync.service import SyncService


class AgentSelectedContextAssemblerTest(IsolatedAsyncioTestCase):
    async def test_assemble_uses_selected_context_messages_not_all_candidates(self) -> None:
        manager = SyncConnectionManager()
        sync_service = SyncService(manager)
        await sync_service.register_session(
            "feishu:oc_test:om_test",
            source="feishu",
            title="飞书群聊新会话",
            summary="等待选择上下文",
            status="等待选择",
            context_messages=[
                {"role": "user", "content": "不要进入 prompt 的候选消息"},
                {"role": "user", "content": "选中的上下文消息"},
            ],
        )
        await sync_service.mark_session_running(
            "feishu:oc_test:om_test",
            context_size=1,
            selected_context_messages=[{"role": "user", "content": "选中的上下文消息"}],
        )

        request = await AgentContextAssembler().assemble(
            AgentChatRequest(session_id="feishu:oc_test:om_test", message="根据上文会议记录总结出文档"),
            sync_service=sync_service,
        )

        contents = [message.content for message in request.context.chat_history] if request.context else []
        self.assertIn("选中的上下文消息", contents)
        self.assertIn("根据上文会议记录总结出文档", contents)
        self.assertNotIn("不要进入 prompt 的候选消息", contents)
