from __future__ import annotations

from unittest import IsolatedAsyncioTestCase, TestCase

from app.modules.agent.service import AgentService


class _AIPPTServiceStub:
    def __init__(self) -> None:
        self.requests = []

    def create_job_from_request(self, request):
        self.requests.append(request)
        return _PPTJobStub()


class _PPTJobStub:
    job_id = "job_test"
    status = "queued"
    progress = 0
    current_step = "queued"
    download_url = None
    error = None


class _DocumentServiceStub:
    def __init__(self) -> None:
        self.requests = []

    async def generate_document(self, request):  # noqa: ANN001
        self.requests.append(request)
        return "doc content"


class _FeishuServiceStub:
    async def create_board_document(self, title):  # noqa: ANN001
        return {
            "document_id": "doc_test",
            "whiteboard_id": "wb_test",
            "sharing_url": "https://example.feishu.cn/docx/doc_test",
        }


class _CanvasServiceStub:
    def __init__(self) -> None:
        self.requests = []

    def create_board_task(self, request):  # noqa: ANN001
        self.requests.append(request)
        return type("BoardTask", (), {"task_id": "board_task_test"})()

    def run_board_task(self, task_id):  # noqa: ANN001
        return type(
            "CompletedBoardTask",
            (),
            {
                "model_dump": lambda self: {
                    "task_id": task_id,
                    "message": "",
                    "sharing_url": "https://example.feishu.cn/docx/doc_test",
                    "status": "succeeded",
                    "current_step": "succeeded",
                    "render_mode": "import_diagram",
                    "whiteboard_id": "wb_test",
                    "preview_url": None,
                    "ticket_id": None,
                    "node_ids": [],
                    "deleted_count": None,
                    "logs": [],
                    "result_summary": None,
                    "error_message": None,
                }
            },
        )()


class AgentPPTDesignModeTest(TestCase):
    def test_resolves_free_design_from_user_message(self) -> None:
        service = AgentService.__new__(AgentService)

        mode = service._resolve_ppt_design_mode(message="帮我生成一份自由设计模式的产品发布 PPT，8 页")

        self.assertEqual(mode, "free_design")

    def test_requested_design_mode_wins_over_message_default(self) -> None:
        service = AgentService.__new__(AgentService)

        mode = service._resolve_ppt_design_mode(requested="free-design", message="帮我生成 PPT")

        self.assertEqual(mode, "free_design")


class AgentRuntimePPTToolDesignModeTest(IsolatedAsyncioTestCase):
    async def test_runtime_ppt_tool_passes_free_design_from_instruction(self) -> None:
        service = AgentService.__new__(AgentService)
        service._aippt_service = _AIPPTServiceStub()

        result = await service._runtime_ppt_tool(
            instruction="帮我用自由设计模式生成一份 AI 项目汇报 PPT，6 页",
            session_id="session_test",
        )

        self.assertEqual(result["job_id"], "job_test")
        self.assertEqual(service._aippt_service.requests[0].design_mode, "free_design")


class AgentRuntimeDocxToolContextTest(IsolatedAsyncioTestCase):
    async def test_runtime_docx_tool_passes_chat_history_to_document_request(self) -> None:
        service = AgentService.__new__(AgentService)
        service._document_service = _DocumentServiceStub()
        service._sync_service = None

        await service._runtime_docx_tool(
            instruction="根据上文会议记录总结出文档",
            session_id="session_test",
            chat_history=[
                {"role": "user", "content": "可以先做文档上传、切块、检索和会话页。"},
                {"role": "user", "content": "团队管理可以先放到二级入口。"},
            ],
        )

        request = service._document_service.requests[0]
        self.assertEqual([message.content for message in request.chat_history], [
            "可以先做文档上传、切块、检索和会话页。",
            "团队管理可以先放到二级入口。",
        ])

    async def test_runtime_board_tool_passes_chat_history_to_canvas_request(self) -> None:
        service = AgentService.__new__(AgentService)
        service._feishu = _FeishuServiceStub()
        service._canvas_service = _CanvasServiceStub()

        await service._runtime_board_tool(
            instruction="根据聊天记录生成时序图",
            session_id="session_test",
            chat_history=[
                {"role": "user", "content": "用户提交需求。"},
                {"role": "assistant", "content": "系统读取上下文并生成画板。"},
            ],
        )

        message = service._canvas_service.requests[0].message
        self.assertIn("## 飞书群聊上下文", message)
        self.assertIn("user: 用户提交需求。", message)
        self.assertIn("assistant: 系统读取上下文并生成画板。", message)
