from __future__ import annotations

from unittest import TestCase

from app.modules.document.schemas import ChatMessage
from app.modules.document.service import DocumentService


class DocumentMeetingContextPromptTest(TestCase):
    def test_meeting_summary_prompt_excludes_assistant_messages_and_forbids_fabrication(self) -> None:
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

        self.assertIn("只能依据下面保留的用户聊天记录", prompt)
        self.assertIn("没有出现的会议时间、参会人、责任人、日期、数字、项目名，一律写“聊天记录未提供”", prompt)
        self.assertIn("团队知识助手", prompt)
        self.assertIn("RAG 一定要放在第一优先级", prompt)
        self.assertNotIn("智能工作流引擎", prompt)
        self.assertNotIn("2024 年 5 月 20 日", prompt)

    def test_meeting_record_request_is_grounded_to_source_chat_messages(self) -> None:
        service = DocumentService.__new__(DocumentService)

        content = service.ground_document_if_needed(
            type(
                "Request",
                (),
                {
                    "session_id": "test",
                    "topic": "根据上完会议记录总结出文档",
                    "requirement": "根据上完会议记录总结出文档",
                    "chat_history": [
                        ChatMessage(role="user", content="这周想把团队知识助手的方案收一下，目标是先服务 20 到 50 人的小团队。"),
                        ChatMessage(role="eko", content="建议做智能工作流引擎。"),
                        ChatMessage(role="user", content="销售侧最常被问的是能不能把公司文档传进去直接问，所以 RAG 一定要放在第一优先级。"),
                    ],
                    "knowledge_docs": [],
                },
            )(),
            "会议时间：[请填写具体日期]\n项目复盘与规划会议\n智能工作流引擎",
        )

        self.assertIn("团队知识助手", content)
        self.assertIn("RAG 一定要放在第一优先级", content)
        self.assertIn("聊天记录未提供", content)
        self.assertNotIn("[请填写", content)
        self.assertNotIn("智能工作流引擎", content)

    def test_meeting_summary_prompt_keeps_last_15_source_messages(self) -> None:
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

        self.assertIn("有效会议消息 1", prompt)
        self.assertIn("有效会议消息 15", prompt)
        self.assertNotIn("早期消息 1", prompt)
        self.assertNotIn("早期消息 3", prompt)
        self.assertNotIn("文档生成完成", prompt)
