from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from app.modules.agent.schemas import AgentIntent
from app.modules.agent.service import AgentService, RouterAgent


class _LLMReturnsChat:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"chat","intent":"chat","confidence":0.99,"reason":"仅输入主题"}'


class _LLMReturnsDocx:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"docx","intent":"docx","confidence":0.99,"reason":"策略文档"}'


class _LLMReturnsBoard:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"board","intent":"board","confidence":0.99,"reason":"生成时序图"}'


class _LLMReturnsLowConfidence:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"docx","intent":"docx","confidence":0.2,"reason":"不确定"}'


class AgentIntentRoutingTest(IsolatedAsyncioTestCase):
    async def test_bare_strategy_topic_stays_chat_not_docx(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        intent = await router.classify_chat_intent("NovaMind 模型分级策略")

        self.assertEqual(intent, AgentIntent.CHAT)

    async def test_bare_strategy_topic_stays_chat_even_if_model_selects_docx(self) -> None:
        router = RouterAgent(_LLMReturnsDocx())

        intent = await router.classify_chat_intent("NovaMind 模型分级策略")

        self.assertEqual(intent, AgentIntent.CHAT)

    async def test_sequence_diagram_request_uses_model_board_intent(self) -> None:
        router = RouterAgent(_LLMReturnsBoard())

        intent = await router.classify_chat_intent("根据聊天记录生成时序图")

        self.assertEqual(intent, AgentIntent.BOARD)

    async def test_explicit_ppt_generation_uses_local_ppt_intent_even_if_model_selects_chat(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        intent = await router.classify_chat_intent("生成舞蹈ppt")

        self.assertEqual(intent, AgentIntent.PPT)

    async def test_chart_generation_uses_local_board_intent_even_if_model_selects_chat(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        for message in ["生成一个测试饼图", "帮我做个销售柱状图", "draw a line chart"]:
            with self.subTest(message=message):
                intent = await router.classify_chat_intent(message)

                self.assertEqual(intent, AgentIntent.BOARD)

    async def test_low_confidence_route_requests_clarification(self) -> None:
        router = RouterAgent(_LLMReturnsLowConfidence())

        route = await router.route_chat_intent("帮我处理一下这个")

        self.assertTrue(route.needs_clarification)
        self.assertIn("直接讨论", [option.label for option in route.clarification_options])
        self.assertIn("生成文档", [option.label for option in route.clarification_options])

    async def test_explicit_ppt_route_does_not_request_clarification(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        route = await router.route_chat_intent("生成舞蹈ppt")

        self.assertFalse(route.needs_clarification)
        self.assertEqual(route.intent, "ppt")

    async def test_current_artifact_vague_edit_requests_clarification(self) -> None:
        from app.modules.agent.schemas import AgentChatArtifact

        router = RouterAgent(_LLMReturnsChat())

        route = await router.route_chat_intent(
            "帮我整理一下这个",
            current_artifact=AgentChatArtifact(kind="ppt", job_id="job_test"),
        )

        self.assertTrue(route.needs_clarification)
        self.assertIn("修改当前PPT", [option.label for option in route.clarification_options])


class _SyncSession:
    messages = [
        {"role": "user", "content": "NovaMind 模型分级策略"},
        {"role": "assistant", "content": "你是想直接讨论这个主题，还是生成一份文档、PPT 或画板？"},
    ]


class _SyncService:
    async def get_session(self, _session_id: str) -> _SyncSession:
        return _SyncSession()


class AgentPendingRouteReplyTest(IsolatedAsyncioTestCase):
    async def test_clarification_reply_restores_original_message_and_forces_intent(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest

        service = AgentService.__new__(AgentService)
        service._sync_service = _SyncService()

        request = await service._resolve_pending_route_reply(
            AgentChatRequest(session_id="s1", message="生成文档")
        )

        self.assertEqual(request.message, "NovaMind 模型分级策略")
        self.assertEqual(request.forced_intent, "docx")
