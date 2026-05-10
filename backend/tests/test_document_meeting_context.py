from __future__ import annotations

from unittest import IsolatedAsyncioTestCase, TestCase

from app.modules.document.schemas import ChatMessage
from app.modules.document.service import DocumentService


class DocumentMeetingContextPromptTest(TestCase):
    def test_chat_history_prompt_passes_selected_messages_without_summary_template_constraints(self) -> None:
        service = DocumentService.__new__(DocumentService)

        prompt = service._get_user_prompt(
            topic="根据聊天记录生成会议总结文档",
            requirement="根据聊天记录生成会议总结文档",
            chat_history=[
                ChatMessage(role="user", content="这周想把团队知识助手的方案收一下，目标是先服务 20 到 50 人的小团队。"),
                ChatMessage(role="eko", content="我建议补充 Eko 2.0 智能工作流引擎和多模态交互升级。"),
                ChatMessage(role="assistant", content="会议时间是 2024 年 5 月 20 日。"),
                ChatMessage(role="user", content="销售侧最常被问的是能不能把公司文档传进去直接问，所以 RAG 一定要放在第一优先级。"),
            ],
            knowledge_docs=[],
            bitable_records=[],
        )

        self.assertIn("## 飞书群聊上下文", prompt)
        self.assertIn("团队知识助手", prompt)
        self.assertIn("RAG 一定要放在第一优先级", prompt)
        self.assertIn("智能工作流引擎", prompt)
        self.assertIn("2024 年 5 月 20 日", prompt)
        self.assertNotIn("聊天记录纪要约束", prompt)
        self.assertNotIn("只能依据下面保留的用户聊天记录", prompt)

    def test_chat_history_prompt_keeps_all_selected_messages(self) -> None:
        service = DocumentService.__new__(DocumentService)

        prompt = service._get_user_prompt(
            topic="根据上完会议记录总结出文档",
            requirement="根据上完会议记录总结出文档",
            chat_history=[
                *[ChatMessage(role="user", content=f"早期消息 {index}") for index in range(1, 4)],
                *[ChatMessage(role="user", content=f"有效会议消息 {index}") for index in range(1, 16)],
                ChatMessage(role="assistant", content="文档生成完成，并已同步到飞书。"),
            ],
            knowledge_docs=[],
            bitable_records=[],
        )

        self.assertIn("早期消息 1", prompt)
        self.assertIn("早期消息 3", prompt)
        self.assertIn("有效会议消息 1", prompt)
        self.assertIn("有效会议消息 15", prompt)
        self.assertIn("文档生成完成", prompt)


class _LLMCapture:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return "# 基于聊天记录的讨论总结\n\n## 讨论要点\n- 同意，团队管理可以先放到二级入口。\n"

    async def generate_stream(self, system_prompt: str, user_prompt: str):
        self.calls.append((system_prompt, user_prompt))
        yield "# 基于聊天记录的讨论总结\n"


class DocumentMeetingContextGenerationTest(IsolatedAsyncioTestCase):
    async def test_chat_record_summary_generation_uses_general_llm_prompt_without_template_limits(self) -> None:
        llm = _LLMCapture()
        service = DocumentService(llm_client=llm, feishu_service=object())

        content = await service.generate_document(
            type(
                "Request",
                (),
                {
                    "session_id": "test",
                    "topic": "根据上文会议记录总结出文档",
                    "requirement": "根据上文会议记录总结出文档",
                    "tone": "formal",
                    "chat_history": [
                        ChatMessage(role="user", content="同意，团队管理可以先放到二级入口，不要一开始压到用户面前。"),
                    ],
                    "knowledge_docs": [],
                    "bitable_records": [],
                },
            )()
        )

        self.assertEqual(len(llm.calls), 1)
        system_prompt, user_prompt = llm.calls[0]
        self.assertIn("文档生成模块", system_prompt)
        self.assertNotIn("不要把简短讨论包装成正式会议纪要", system_prompt)
        self.assertIn("同意，团队管理可以先放到二级入口", user_prompt)
        self.assertNotIn("聊天记录纪要约束", user_prompt)
        self.assertIn("团队管理可以先放到二级入口", content)
