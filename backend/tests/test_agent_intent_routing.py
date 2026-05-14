from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from app.modules.agent.schemas import AgentIntent
from app.modules.agent.service import RouterAgent


class _LLMReturnsChat:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"chat","intent":"chat","confidence":0.99,"reason":"仅输入主题"}'


class _LLMReturnsDocx:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"docx","intent":"docx","confidence":0.99,"reason":"策略文档"}'


class _LLMReturnsBoard:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"board","intent":"board","confidence":0.99,"reason":"生成时序图"}'


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
