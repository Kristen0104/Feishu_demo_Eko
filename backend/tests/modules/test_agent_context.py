from __future__ import annotations

import asyncio

from app.modules.agent.context import AgentContextAssembler
from app.modules.agent.schemas import AgentChatRequest, AgentContext, ChatMessage
from app.modules.sync.schemas import SyncContextMessageSchema, SyncSessionMessageSchema


class FakeSyncService:
    def __init__(self) -> None:
        self.context_messages = [
            SyncContextMessageSchema(role="user", content="飞书群里先讨论了动画行业背景", timestamp=1),
        ]
        self.messages = [
            SyncSessionMessageSchema(role="user", content="重新生成一份2页PPT，主题是「动画发展」。", timestamp=2),
            SyncSessionMessageSchema(
                role="assistant",
                content="你希望用「模板模式」快速稳定生成，还是用「自由设计」做更强视觉表现？",
                timestamp=3,
            ),
        ]

    async def get_session(self, session_id: str):  # type: ignore[no-untyped-def]
        class Session:
            def __init__(self, context_messages, messages):  # type: ignore[no-untyped-def]
                self.context_messages = context_messages
                self.messages = messages

        return Session(self.context_messages, self.messages)


def test_agent_context_assembler_merges_sync_frontend_and_current_message() -> None:
    request = AgentChatRequest(
        session_id="s1",
        message="模板",
        context=AgentContext(
            chat_history=[
                ChatMessage(role="user", content="重新生成一份2页PPT，主题是「动画发展」。", timestamp=2),
                ChatMessage(role="user", content="模板"),
            ]
        ),
    )

    assembled = asyncio.run(AgentContextAssembler().assemble(request, sync_service=FakeSyncService()))

    assert assembled.context is not None
    assert [message.content for message in assembled.context.chat_history] == [
        "飞书群里先讨论了动画行业背景",
        "重新生成一份2页PPT，主题是「动画发展」。",
        "你希望用「模板模式」快速稳定生成，还是用「自由设计」做更强视觉表现？",
        "模板",
    ]


def test_agent_context_assembler_preserves_request_knowledge_docs() -> None:
    request = AgentChatRequest(
        session_id="s1",
        message="继续",
        context=AgentContext(
            knowledge_docs=[{"title": "品牌规范", "content": "使用蓝色主色", "source": "doc-1"}],
        ),
    )

    assembled = asyncio.run(AgentContextAssembler().assemble(request, sync_service=None))

    assert assembled.context is not None
    assert assembled.context.knowledge_docs[0].title == "品牌规范"
    assert assembled.context.chat_history[-1].content == "继续"
