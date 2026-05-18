from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from app.modules.agent.schemas import AgentChatRequest, AgentPlanFinalOutput, AgentTaskPlan
from app.modules.agent.service import AgentService


class _LLMStub:
    async def generate(self, *_: object, **__: object) -> str:
        return '{"goal":"test","intent":"chat","summary":"test","visible_summary":"test","steps":[],"final_output":{"format":"text","requirements":[]}}'

    async def generate_stream(self, *_: object, **__: object):
        yield "# Stub 文档\n\n内容生成成功。"


class _FeishuServiceStub:
    def __init__(self) -> None:
        self._client = None
        self.created_boards: list[str] = []
        self.sent_messages: list[tuple[str, str]] = []

    async def create_board_document(self, title: str) -> dict[str, str]:
        self.created_boards.append(title)
        return {
            "document_id": "doc_board",
            "whiteboard_id": "wb_board",
            "sharing_url": "https://example.feishu.cn/docx/doc_board",
        }

    async def add_docx_permission_for_chat(self, *_: object, **__: object) -> dict[str, object]:
        return {}

    async def send_text_message_to_chat(self, chat_id: str, text: str) -> dict[str, object]:
        self.sent_messages.append((chat_id, text))
        return {}

    async def publish_markdown_to_feishu(self, *_: object, **__: object) -> dict[str, object]:
        return {"document_url": "https://example.feishu.cn/docx/doc_docx", "record_id": None}

    async def get_message(self, _message_id: str) -> None:
        return None


class _DocumentServiceStub:
    def __init__(self) -> None:
        self.requests: list[object] = []

    async def generate_document(self, _request: object) -> str:
        self.requests.append(_request)
        return "# Stub 文档\n\n内容生成成功。"

    async def generate_document_stream(self, _request: object):
        self.requests.append(_request)
        yield "# Stub 文档\n\n内容生成成功。"

    def ground_document_if_needed(self, _request: object, content: str) -> str:
        return content

    async def edit_document(self, request: object) -> str:
        return f"{getattr(request, 'current_content', '')}\n已编辑。"


class _PPTJobStub:
    job_id = "job_stub"
    status = "queued"
    progress = 0
    current_step = "queued"
    download_url = None
    error = None


class _AIPPTServiceStub:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def create_job_from_request(self, request: object) -> _PPTJobStub:
        self.requests.append(request)
        return _PPTJobStub()

    def get_preview(self, job_id: str) -> dict[str, object]:
        return {
            "job_id": job_id,
            "title": "Stub PPT",
            "page_count": 3,
            "design_mode": "template",
            "slides": [],
        }


class _CanvasServiceStub:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def create_board_task(self, request: object) -> object:
        self.requests.append(request)
        return type("BoardTask", (), {"task_id": "board_task_stub"})()

    def run_board_task(self, task_id: str) -> object:
        latest_request = self.requests[-1]
        return type(
            "CompletedBoardTask",
            (),
            {
                "task_id": task_id,
                "message": latest_request.message,
                "sharing_url": latest_request.sharing_url,
                "status": "succeeded",
                "current_step": "succeeded",
                "render_mode": "create_notes",
                "whiteboard_id": "wb_board",
                "preview_url": "https://example.feishu.cn/preview.png",
                "ticket_id": None,
                "node_ids": ["n1", "n2"],
                "deleted_count": 0,
                "logs": [],
                "result_summary": "board ok",
                "error_message": None,
            },
        )()


class AgentGenerationChainsTest(IsolatedAsyncioTestCase):
    def _service(self) -> tuple[AgentService, _AIPPTServiceStub, _CanvasServiceStub]:
        ppt = _AIPPTServiceStub()
        canvas = _CanvasServiceStub()
        service = AgentService(
            _LLMStub(),
            _FeishuServiceStub(),
            _DocumentServiceStub(),
            canvas,
            aippt_service=ppt,
            sync_service=None,
        )
        service._schedule_ppt_job = lambda _request, _job_id: None  # type: ignore[method-assign]
        return service, ppt, canvas

    async def test_docx_chain_generates_document_artifact(self) -> None:
        service, _, _ = self._service()

        response = await service.chat(
            AgentChatRequest(
                session_id="local-docx",
                message="生成一份测试文档",
                forced_intent="docx",
                planning_enabled=False,
            )
        )

        self.assertEqual(response.status, "completed")
        self.assertIsNotNone(response.artifact)
        self.assertEqual(response.artifact.kind, "docx")
        self.assertIn("内容生成成功", response.artifact.content or "")

    async def test_docx_chain_generates_document_once_when_planning_enabled(self) -> None:
        service, _, _ = self._service()

        response = await service.chat(
            AgentChatRequest(
                session_id="local-docx-once",
                message="生成一份测试文档",
                forced_intent="docx",
                planning_enabled=True,
            )
        )

        self.assertEqual(response.status, "completed")
        self.assertEqual(response.artifact.kind if response.artifact else None, "docx")
        self.assertEqual(service._document_service.requests.__len__(), 1)

    async def test_docx_chain_does_not_pause_for_planner_clarification(self) -> None:
        service, _, _ = self._service()

        async def _clarifying_plan(_request: object, _intent: object) -> AgentTaskPlan:
            return AgentTaskPlan(
                goal="生成奶龙文档",
                intent="doc_generation",
                summary="需要更多信息",
                visible_summary="需要更多信息",
                need_clarification=True,
                clarification_needed=True,
                clarification_question="请问您希望生成的奶龙文档具体是什么内容？",
                questions=["请问您希望生成的奶龙文档具体是什么内容？"],
                final_output=AgentPlanFinalOutput(format="markdown_document", requirements=[]),
            )

        service._create_plan_with_timeout = _clarifying_plan  # type: ignore[method-assign]

        response = await service.chat(
            AgentChatRequest(
                session_id="local-docx-clarification",
                message="生成奶龙文档",
                forced_intent="docx",
            )
        )

        self.assertEqual(response.status, "completed")
        self.assertIsNotNone(response.artifact)
        self.assertEqual(response.artifact.kind, "docx")
        self.assertEqual(response.message, "文档生成完成。")

    async def test_ppt_chain_creates_job_without_planner_tool_result(self) -> None:
        service, ppt, _ = self._service()

        response = await service.chat(
            AgentChatRequest(
                session_id="local-ppt",
                message="生成一份3页测试PPT",
                forced_intent="ppt",
                planning_enabled=False,
            )
        )

        self.assertEqual(response.status, "completed")
        self.assertIsNotNone(response.artifact)
        self.assertEqual(response.artifact.kind, "ppt")
        self.assertEqual(response.artifact.job_id, "job_stub")
        self.assertEqual(ppt.requests[0].page_count, 3)

    async def test_board_chain_generates_board_artifact_once(self) -> None:
        service, _, canvas = self._service()

        response = await service.chat(
            AgentChatRequest(
                session_id="local-board",
                message="生成一个测试画板",
                forced_intent="board",
                planning_enabled=False,
            )
        )

        self.assertEqual(response.status, "completed")
        self.assertIsNotNone(response.artifact)
        self.assertEqual(response.artifact.kind, "board")
        self.assertEqual(response.artifact.whiteboard_id, "wb_board")
        self.assertEqual(response.artifact.sharing_url, "https://example.feishu.cn/docx/doc_board")
        self.assertEqual(len(canvas.requests), 1)
        self.assertIn("## 用户需求", canvas.requests[0].message)
