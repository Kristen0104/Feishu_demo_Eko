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
