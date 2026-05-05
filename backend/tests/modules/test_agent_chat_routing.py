from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.agent.dependencies import get_agent_service
from app.modules.agent.router import router as agent_router
from app.modules.agent.schemas import AgentChatRequest, AgentChatResponse, AgentContext, ChatMessage
from app.modules.agent.service import AgentService
from app.modules.canvas.schemas import CanvasBoardTaskSchema
from app.modules.document.schemas import DocumentEditRequest, DocumentGenerationRequest
from app.modules.feishu.service import FeishuService
from app.modules.aippt.schemas import PPTGenerationRequest, PPTJobSchema
from app.modules.sync.schemas import SyncSessionMessageSchema


class FakeLLMClient:
    def __init__(self, intent: str = "chat", reply: str = "你好，我是 Eko。") -> None:
        self.intent = intent
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        if "意图" in system_prompt or "intent" in system_prompt.lower():
            return self.intent
        return self.reply


class FailingIntentLLMClient(FakeLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        if "意图" in system_prompt or "intent" in system_prompt.lower():
            raise RuntimeError("classifier unavailable")
        return self.reply


class EmptyIntentLLMClient(FakeLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        if "意图" in system_prompt or "intent" in system_prompt.lower():
            return ""
        return self.reply


class JsonIntentLLMClient(FakeLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        if "意图" in system_prompt or "intent" in system_prompt.lower():
            return '{"intent":"ppt","confidence":0.91,"reason":"用户要汇报材料"}'
        return self.reply


class JsonBoardToolIntentLLMClient(FakeLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        if "工具选择器" in system_prompt or "primary_tool" in system_prompt:
            return '{"primary_tool":"board","intent":"board","confidence":0.96,"reason":"用户要思路图"}'
        return self.reply


class ClarifyingPlannerLLMClient(FakeLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        if "高级意图识别器" in system_prompt or "可选意图" in system_prompt:
            return "docx"
        return """
        {
          "goal": "生成市场分析报告",
          "intent": "report_generation",
          "task_complexity": "complex",
          "missing_info": ["时间范围"],
          "need_clarification": true,
          "questions": ["报告覆盖哪个时间范围？"],
          "assumptions": [],
          "summary": "需要先补充时间范围再生成报告",
          "steps": [
            {
              "id": "step_1",
              "title": "收集约束",
              "description": "确认报告时间范围",
              "type": "clarification",
              "tool": null,
              "input": {},
              "expected_output": "明确时间范围",
              "depends_on": []
            }
          ],
          "final_output": {"format": "markdown_report", "requirements": ["结构清晰"]}
        }
        """


class SlowPlannerLLMClient(FakeLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        if "高级意图识别器" in system_prompt or "可选意图" in system_prompt:
            return "chat"
        await asyncio.sleep(10)
        return self.reply


class FakeDocumentService:
    def __init__(self) -> None:
        self.requests: list[DocumentGenerationRequest] = []
        self.edit_requests: list[DocumentEditRequest] = []

    async def generate_document(self, request: DocumentGenerationRequest) -> str:
        self.requests.append(request)
        return "# 方案\n\n文档内容"

    async def edit_document(self, request: DocumentEditRequest) -> str:
        self.edit_requests.append(request)
        return "# 方案\n\n正文"


class FakeAIPPTService:
    def __init__(self) -> None:
        self.requests: list[PPTGenerationRequest] = []
        self.enqueued_job_ids: list[str] = []
        self.get_job_calls: list[str] = []
        self.final_status = "done"
        self.final_progress = 100
        self.final_step = "导出完成"
        self.final_download_url = "/api/v1/ppt/files/aippt-job-1"
        self.final_error: str | None = None
        self.preview = {
            "job_id": "aippt-old",
            "title": "环保主题 PPT",
            "page_count": 6,
            "slides": [
                {"slide_number": 1, "title": "封面", "right_items": ["环保主题"]},
                {"slide_number": 2, "title": "背景与问题", "right_items": ["气候变化", "资源压力"]},
                {"slide_number": 3, "title": "行动方案", "right_items": ["低碳出行", "绿色消费"]},
                {"slide_number": 4, "title": "案例", "right_items": ["城市实践"]},
                {"slide_number": 5, "title": "收益", "right_items": ["环境价值", "社会价值"]},
                {"slide_number": 6, "title": "总结", "right_items": ["下一步行动"]},
            ],
        }

    def create_job_from_request(self, payload: PPTGenerationRequest) -> PPTJobSchema:
        self.requests.append(payload)
        return PPTJobSchema(
            job_id="aippt-job-1",
            status="queued",
            progress=0,
            current_step="任务已入队",
            source_type="topic",
            source_name=payload.topic,
            page_count=payload.page_count,
            style=payload.style,
            design_mode=payload.design_mode,
            download_url="/api/v1/ppt/files/aippt-job-1",
            created_at="2026-05-03T00:00:00+00:00",
            updated_at="2026-05-03T00:00:00+00:00",
        )

    def enqueue_job(self, job_id: str) -> None:
        self.enqueued_job_ids.append(job_id)

    def get_job(self, job_id: str) -> PPTJobSchema:
        assert job_id == "aippt-job-1"
        self.get_job_calls.append(job_id)
        return PPTJobSchema(
            job_id="aippt-job-1",
            status=self.final_status,
            progress=self.final_progress,
            current_step=self.final_step,
            source_type="topic",
            source_name=self.requests[-1].topic if self.requests else None,
            page_count=self.requests[-1].page_count if self.requests else 6,
            style=self.requests[-1].style if self.requests else "clean_business",
            design_mode=self.requests[-1].design_mode if self.requests else "template",
            download_url=self.final_download_url,
            error=self.final_error,
            created_at="2026-05-03T00:00:00+00:00",
            updated_at="2026-05-03T00:00:06+00:00",
        )

    def get_preview(self, job_id: str) -> dict[str, object]:
        assert job_id in {"aippt-old", "aippt-job-1"}
        preview = dict(self.preview)
        preview["job_id"] = job_id
        return preview


class FakeCanvasService:
    def __init__(self) -> None:
        self.created_messages: list[str] = []
        self.created_sharing_urls: list[str | None] = []
        self.run_task_ids: list[str] = []

    def create_board_task(self, payload):
        self.created_messages.append(payload.message)
        self.created_sharing_urls.append(payload.sharing_url)
        return CanvasBoardTaskSchema(
            task_id="board-task-1",
            message=payload.message,
            sharing_url=payload.sharing_url,
            render_mode="create_notes",
        )

    def run_board_task(self, task_id: str) -> CanvasBoardTaskSchema:
        self.run_task_ids.append(task_id)
        return CanvasBoardTaskSchema(
            task_id=task_id,
            message=self.created_messages[-1],
            sharing_url="https://example.feishu.cn/wiki/board/wbcn123",
            status="succeeded",
            current_step="succeeded",
            render_mode="create_notes",
            whiteboard_id="wbcn123",
            preview_url="https://stub.preview/wbcn123.png",
            ticket_id="ticket-wbcn123",
            node_ids=["node-1"],
            result_summary="已同步飞书画板",
        )


class FailingCanvasService(FakeCanvasService):
    def run_board_task(self, task_id: str) -> CanvasBoardTaskSchema:
        self.run_task_ids.append(task_id)
        return CanvasBoardTaskSchema(
            task_id=task_id,
            message=self.created_messages[-1],
            sharing_url="https://example.feishu.cn/wiki/board/wbcn123",
            status="failed",
            current_step="failed",
            render_mode="create_notes",
            error_message="Feishu board request failed",
        )


class RecordingFeishuService:
    def __init__(self) -> None:
        self._client = None
        self.created_board_documents: list[str] = []
        self.granted_permissions: list[tuple[str, str, str]] = []
        self.sent_messages: list[tuple[str, str]] = []
        self.published_markdown: list[tuple[str, str]] = []

    async def create_board_document(self, title: str) -> dict[str, str]:
        self.created_board_documents.append(title)
        return {
            "document_id": "docx_board_1",
            "whiteboard_id": "wbcn123",
            "sharing_url": "https://example.feishu.cn/docx/docx_board_1",
        }

    async def add_docx_permission_for_chat(
        self,
        document_id: str,
        chat_id: str,
        *,
        perm: str = "edit",
    ) -> dict[str, str]:
        self.granted_permissions.append((document_id, chat_id, perm))
        return {"member_id": chat_id, "perm": perm}

    async def send_text_message_to_chat(self, chat_id: str, text: str) -> dict[str, str]:
        self.sent_messages.append((chat_id, text))
        return {"message_id": "msg_1"}

    async def publish_markdown_to_feishu(
        self,
        title: str,
        markdown_content: str,
        app_token: str | None = None,
        table_id: str | None = None,
        ticket: str | None = None,
    ) -> dict[str, object]:
        self.published_markdown.append((title, markdown_content))
        return {
            "document_url": "https://example.feishu.cn/docx/docx_doc_1",
            "record_id": None,
            "status": "success",
        }


class RecordingSyncService:
    def __init__(self, artifact: dict[str, object] | None = None, messages: list[dict[str, object]] | None = None) -> None:
        self.completed: list[dict[str, object]] = []
        self.errors: list[dict[str, object]] = []
        self.artifact = artifact
        self.messages: list[dict[str, object]] = messages or []

    async def get_session(self, session_id: str):  # type: ignore[no-untyped-def]
        class Session:
            def __init__(self, artifact, messages):  # type: ignore[no-untyped-def]
                self.artifact = artifact
                self.messages = messages

        return Session(self.artifact, self.messages)

    async def publish_task_completed(
        self,
        session_id: str,
        *,
        intent: str,
        message: str,
        status: str,
        artifact: dict[str, object] | None = None,
        messages: list[dict[str, object]] | None = None,
        error: str | None = None,
    ) -> None:
        self.completed.append(
            {
                "session_id": session_id,
                "intent": intent,
                "message": message,
                "status": status,
                "artifact": artifact,
                "messages": messages,
                "error": error,
            }
        )

    async def publish_error(self, session_id: str, message: str, error: str | None = None) -> None:
        self.errors.append(
            {
                "session_id": session_id,
                "message": message,
                "error": error,
            }
        )


def build_client(service: AgentService) -> TestClient:
    app = FastAPI()
    app.include_router(agent_router, prefix="/api/v1/agent")
    app.dependency_overrides[get_agent_service] = lambda: service
    return TestClient(app)


def event_names(events: list[dict[str, object]]) -> list[str]:
    return [str(event["event"]) for event in events]


def event_payload(event: dict[str, object]) -> dict[str, object]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def make_service(intent: str, reply: str = "你好，我是 Eko。") -> AgentService:
    return AgentService(
        llm_client=FakeLLMClient(intent=intent, reply=reply),
        feishu_service=FeishuService(client=None),  # not used by these routed paths
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )


def test_agent_chat_returns_basic_volcengine_reply() -> None:
    service = make_service("chat", reply="当然可以，我们开始。")

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "你好"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "chat"
    assert payload["status"] == "completed"
    assert payload["message"] == "当然可以，我们开始。"
    assert payload["artifact"] is None


def test_agent_chat_uses_rag_context_for_plain_question() -> None:
    llm_client = FakeLLMClient(intent="chat", reply="星途智能总部在北京海淀。")
    service = AgentService(
        llm_client=llm_client,
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "星途智能总部在哪？",
                "context": {
                    "knowledge_docs": [
                        {
                            "title": "星途资料",
                            "content": "星途智能科技有限公司总部坐落于北京海淀人工智能产业核心集聚区。",
                            "source": "rag-file",
                        }
                    ]
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "chat"
    assert payload["message"] == "星途智能总部在北京海淀。"
    answer_prompt = llm_client.calls[-1][1]
    assert "## RAG 知识库资料" in answer_prompt
    assert "北京海淀人工智能产业核心集聚区" in answer_prompt


def test_agent_chat_routes_docx_to_document_service() -> None:
    service = make_service("docx")

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "写一份活动方案"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "docx"
    assert payload["artifact"]["kind"] == "docx"
    assert payload["artifact"]["content"].startswith("# 方案")


def test_agent_chat_docx_runs_through_runtime_tool_node() -> None:
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="docx"),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "写一份活动方案"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["artifact"]["content"].startswith("# 方案")
    assert len(document_service.requests) == 1
    assert "tool.completed" in event_names(payload["events"])


def test_agent_chat_docx_passes_context_docs_to_document_service() -> None:
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="docx"),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "基于知识库写公司介绍",
                "context": {
                    "knowledge_docs": [
                        {
                            "title": "星途资料",
                            "content": "总部坐落于北京海淀，在深圳、杭州设有两大研发中心。",
                            "source": "rag-file",
                        }
                    ]
                },
            },
        )

    assert response.status_code == 200
    assert len(document_service.requests) == 1
    assert document_service.requests[0].knowledge_docs[0].title == "星途资料"
    assert "北京海淀" in document_service.requests[0].knowledge_docs[0].content


def test_agent_chat_natural_language_text_generation_routes_docx_without_explicit_doc_word() -> None:
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "生成苹果公司介绍 100 字"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "docx"
    assert payload["artifact"]["kind"] == "docx"
    assert len(document_service.requests) == 1


def test_agent_chat_edits_current_docx_without_regenerating() -> None:
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="docx"),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "删除总结部分可以吗",
                "current_document": {
                    "kind": "docx",
                    "content": "# 方案\n\n正文\n\n## 总结\n\n这里是总结",
                    "sharing_url": "https://example.feishu.cn/docx/docx_doc_1",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "docx"
    assert payload["message"] == "已修改当前文档。"
    assert payload["artifact"]["content"] == "# 方案\n\n正文"
    assert payload["artifact"]["sharing_url"] == "https://example.feishu.cn/docx/docx_doc_1"
    assert document_service.requests == []
    assert len(document_service.edit_requests) == 1


def test_agent_chat_syncs_edited_docx_to_feishu_chat_when_session_is_feishu() -> None:
    feishu_service = RecordingFeishuService()
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="docx"),
        feishu_service=feishu_service,  # type: ignore[arg-type]
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "feishu:oc_chat_1:om_msg_2",
                "message": "删除总结部分，并同步到飞书",
                "current_document": {
                    "kind": "docx",
                    "content": "# 方案\n\n正文\n\n## 总结\n\n这里是总结",
                    "sharing_url": "https://example.feishu.cn/docx/old_doc",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["message"] == "已修改当前文档，并已同步到飞书。"
    assert payload["artifact"]["content"] == "# 方案\n\n正文"
    assert payload["artifact"]["sharing_url"] == "https://example.feishu.cn/docx/docx_doc_1"
    assert document_service.requests == []
    assert len(document_service.edit_requests) == 1
    assert feishu_service.published_markdown == [("Eko 文档 - 删除总结部分，并同步到飞书", "# 方案\n\n正文")]
    assert feishu_service.granted_permissions == [("docx_doc_1", "oc_chat_1", "edit")]
    assert feishu_service.sent_messages == [
        ("oc_chat_1", "Eko 已更新飞书文档：\nhttps://example.feishu.cn/docx/docx_doc_1")
    ]


def test_agent_chat_keeps_docx_edit_when_instruction_mentions_business_dashboard() -> None:
    feishu_service = RecordingFeishuService()
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="board"),
        feishu_service=feishu_service,  # type: ignore[arg-type]
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "feishu:oc_chat_1:om_msg_3",
                "message": "把负责人动作清单里新增一条：客户成功负责人每周五同步续费风险看板，并同步到飞书。",
                "current_document": {
                    "kind": "docx",
                    "content": "# 客户续费风险分析\n\n## 负责人动作清单\n\n- 每周复盘客户风险",
                    "sharing_url": "https://example.feishu.cn/docx/old_doc",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "docx"
    assert payload["artifact"]["kind"] == "docx"
    assert document_service.requests == []
    assert len(document_service.edit_requests) == 1


def test_agent_chat_defaults_to_current_docx_for_followup_instruction() -> None:
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "这一版太口语了，改得更正式一点，最后再补一段风险提示",
                "current_document": {
                    "kind": "docx",
                    "content": "# 方案\n\n正文",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "docx"
    assert payload["message"] == "已修改当前文档。"
    assert document_service.requests == []
    assert len(document_service.edit_requests) == 1
    assert document_service.edit_requests[0].instruction == "这一版太口语了，改得更正式一点，最后再补一段风险提示"


def test_agent_chat_can_create_new_docx_when_user_explicitly_asks() -> None:
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="docx"),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "重新生成一份更正式的方案",
                "current_document": {
                    "kind": "docx",
                    "content": "# 旧方案\n\n正文",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "docx"
    assert payload["message"] == "文档生成完成。"
    assert len(document_service.requests) == 1
    assert document_service.edit_requests == []


def test_agent_chat_streams_planning_tool_and_result_events() -> None:
    service = make_service("docx")

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={"session_id": "s1", "message": "写一份活动方案"},
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    names = event_names(events)
    assert names[:6] == [
        "turn.started",
        "intent.recognized",
        "retrieval.started",
        "retrieval.completed",
        "plan.created",
        "plan.summary",
    ]
    assert "plan.step" in names
    assert names[-2:] == ["tool.started", "result.created"]
    assert "sources" in event_payload(events[names.index("retrieval.completed")])
    assert event_payload(events[names.index("plan.created")])["plan"]["intent"] == "doc_generation"
    assert event_payload(events[names.index("plan.created")])["plan"]["steps"][0]["id"] == "step_1"
    assert event_payload(events[-2])["tool"] == "docx"
    assert event_payload(events[-1])["response"]["artifact"]["kind"] == "docx"


def test_agent_chat_stream_continues_with_assumptions_when_details_are_missing() -> None:
    document_service = FakeDocumentService()
    service = AgentService(
        llm_client=ClarifyingPlannerLLMClient(),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={"session_id": "s1", "message": "写一份市场分析报告"},
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    names = event_names(events)
    assert names[:6] == [
        "turn.started",
        "intent.recognized",
        "retrieval.started",
        "retrieval.completed",
        "plan.created",
        "plan.summary",
    ]
    assert "plan.step" in names
    assert "clarification.requested" in names
    assumption = events[names.index("clarification.requested")]
    assert event_payload(assumption)["questions"] == ["报告覆盖哪个时间范围？"]
    assert names[-2:] == ["tool.started", "result.created"]
    assert len(document_service.requests) == 1


def test_agent_chat_stream_edits_current_docx_without_clarification() -> None:
    service = make_service("docx")

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={
                "session_id": "s1",
                "message": "删除总结部分可以吗",
                "current_document": {
                    "kind": "docx",
                    "content": "# 方案\n\n正文\n\n## 总结\n\n这里是总结",
                    "sharing_url": "https://example.feishu.cn/docx/docx_doc_1",
                },
            },
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    names = event_names(events)
    assert names[:4] == ["turn.started", "intent.recognized", "plan.created", "plan.summary"]
    assert "plan.step" in names
    assert names[-2:] == ["tool.started", "result.created"]
    assert events[1]["message"] == "我判断这次是修改当前文档，不会重新生成文档。"
    assert event_payload(events[-2])["tool"] == "docx_edit"
    assert event_payload(events[-1])["response"]["artifact"]["content"] == "# 方案\n\n正文"


def test_agent_chat_can_skip_task_planning() -> None:
    service = make_service("docx")

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "写一份活动方案", "planning_enabled": False},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "docx"
    assert payload["artifact"]["kind"] == "docx"
    assert payload["plan"] is None


def test_agent_chat_syncs_docx_to_feishu_chat_when_session_is_feishu() -> None:
    feishu_service = RecordingFeishuService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="docx"),
        feishu_service=feishu_service,  # type: ignore[arg-type]
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "feishu:oc_chat_1:om_msg_1", "message": "写一份测试文档"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["artifact"]["sharing_url"] == "https://example.feishu.cn/docx/docx_doc_1"
    assert feishu_service.published_markdown[0][0].startswith("Eko 文档")
    assert feishu_service.granted_permissions == [("docx_doc_1", "oc_chat_1", "edit")]
    assert feishu_service.sent_messages == [
        ("oc_chat_1", "Eko 已创建飞书文档：\nhttps://example.feishu.cn/docx/docx_doc_1")
    ]


def test_agent_chat_routes_ppt_to_ai_ppt_job() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "用模板模式生成项目汇报 PPT"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"]["kind"] == "ppt"
    assert payload["artifact"]["job_id"] == "aippt-job-1"
    assert payload["artifact"]["download_url"] == "/api/v1/ppt/files/aippt-job-1"
    assert payload["artifact"]["status"] == "queued"
    assert payload["artifact"]["progress"] == 0
    assert payload["artifact"]["current_step"] == "任务已入队"
    assert payload["plan"]["intent"] == "ppt_generation"
    assert [step["tool"] for step in payload["plan"]["steps"]] == [None, "ppt", "sync"]
    assert "tool.completed" in event_names(payload["events"])
    assert len(aippt_service.requests) == 1


def test_agent_chat_ppt_includes_rag_context_in_topic() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "用模板模式基于知识库生成星途智能 PPT",
                "context": {
                    "knowledge_docs": [
                        {
                            "title": "星途资料",
                            "content": "总部坐落于北京海淀，在深圳、杭州设有研发中心，核心产品是星枢大模型。",
                            "source": "rag-file",
                        }
                    ]
                },
            },
        )

    assert response.status_code == 200
    assert len(aippt_service.requests) == 1
    assert "## RAG 知识库资料" in (aippt_service.requests[0].topic or "")
    assert "北京海淀" in (aippt_service.requests[0].topic or "")
    assert "星枢大模型" in (aippt_service.requests[0].topic or "")


def test_agent_chat_unspecified_ppt_design_mode_asks_clarification() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "生成项目汇报 PPT"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"] is None
    assert "模板模式" in payload["message"]
    assert "自由设计" in payload["message"]
    assert payload["plan"]["need_clarification"] is True
    assert payload["plan"]["visible_summary"]
    assert payload["events"][-1]["event"] == "plan.created"
    assert aippt_service.requests == []


def test_agent_chat_free_design_ppt_request_uses_free_design_mode() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "用自由设计模式生成一份 AI 客服周报 PPT"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"]["kind"] == "ppt"
    assert aippt_service.requests[0].design_mode == "free_design"


def test_agent_chat_ppt_mode_short_reply_continues_pending_generation() -> None:
    aippt_service = FakeAIPPTService()
    sync_service = RecordingSyncService(
        messages=[
            SyncSessionMessageSchema(role="user", content="生成一份2页PPT，主题是「客户成功月报」。"),
            SyncSessionMessageSchema(
                role="assistant",
                content="你希望用「模板模式」快速稳定生成，还是用「自由设计」做更强视觉表现？请回复“模板模式”或“自由设计”。",
            ),
            SyncSessionMessageSchema(role="user", content="模板"),
        ],
    )
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "模板"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"]["kind"] == "ppt"
    assert len(aippt_service.requests) == 1
    assert aippt_service.requests[0].design_mode == "template"
    assert aippt_service.requests[0].page_count == 2
    assert "客户成功月报" in (aippt_service.requests[0].topic or "")
    assert (aippt_service.requests[0].topic or "").strip() != "## 当前指令\n模板"


def test_agent_chat_ppt_mode_short_reply_uses_request_chat_history() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "模板",
                "context": {
                    "chat_history": [
                        {"role": "user", "content": "重新生成一份2页PPT，主题是「动画发展」。"},
                        {
                            "role": "assistant",
                            "content": "你希望用「模板模式」快速稳定生成，还是用「自由设计」做更强视觉表现？请回复“模板模式”或“自由设计”。",
                        },
                        {"role": "user", "content": "模板"},
                    ]
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"]["kind"] == "ppt"
    assert len(aippt_service.requests) == 1
    assert aippt_service.requests[0].design_mode == "template"
    assert aippt_service.requests[0].page_count == 2
    assert "动画发展" in (aippt_service.requests[0].topic or "")


def test_agent_chat_keyword_ppt_cannot_be_downgraded_to_chat() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "用模板模式生成环保主题 ppt"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"]["kind"] == "ppt"
    assert len(aippt_service.requests) == 1


def test_agent_chat_ppt_request_does_not_edit_current_docx() -> None:
    document_service = FakeDocumentService()
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "用模板模式生成文学主题 ppt",
                "current_document": {
                    "kind": "docx",
                    "content": "# 旧文档\n\n正文",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"]["kind"] == "ppt"
    assert document_service.edit_requests == []
    assert len(aippt_service.requests) == 1


def test_agent_chat_stream_ppt_request_does_not_edit_current_docx() -> None:
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={
                "session_id": "s1",
                "message": "用模板模式生成文学主题 ppt",
                "current_document": {
                    "kind": "docx",
                    "content": "# 旧文档\n\n正文",
                },
            },
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    assert event_payload(events[1])["intent"] == "ppt"
    assert event_payload(events[-2])["tool"] == "ppt"
    assert event_payload(events[-1])["response"]["intent"] == "ppt"
    assert "tool.completed" in event_names(event_payload(events[-1])["response"]["events"])
    assert "docx_edit" not in [event_payload(event).get("tool") for event in events]


def test_agent_chat_followup_on_current_ppt_stays_ppt() -> None:
    document_service = FakeDocumentService()
    aippt_service = FakeAIPPTService()
    sync_service = RecordingSyncService(
        artifact={
            "kind": "ppt",
            "job_id": "aippt-old",
            "status": "done",
            "download_url": "/api/v1/ppt/files/aippt-old",
        }
    )
    service = AgentService(
        llm_client=FakeLLMClient(intent="docx"),
        feishu_service=FeishuService(client=None),
        document_service=document_service,
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "第三张文字详细一点"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["message"] == "AI PPT 更新任务已创建，正在保留原结构并修改指定页面。"
    assert payload["artifact"]["kind"] == "ppt"
    assert document_service.edit_requests == []
    assert len(aippt_service.requests) == 1
    assert aippt_service.requests[0].page_count == 6
    topic = aippt_service.requests[0].topic
    assert "## 当前 PPT" in topic
    assert "环保主题 PPT" in topic
    assert "第 3 页：行动方案" in topic
    assert "第三张文字详细一点" in topic
    assert "没有点名的页面不要重写、不要删减" in topic


def test_agent_chat_current_ppt_edit_page_reference_does_not_shrink_deck() -> None:
    aippt_service = FakeAIPPTService()
    aippt_service.preview = {
        **aippt_service.preview,
        "page_count": 3,
        "slides": aippt_service.preview["slides"][:3],
    }
    sync_service = RecordingSyncService(
        artifact={
            "kind": "ppt",
            "job_id": "aippt-old",
            "status": "done",
            "download_url": "/api/v1/ppt/files/aippt-old",
        }
    )
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "只把第2页标题改成「高频问题与处理效率」，其他保持不变"},
        )

    assert response.status_code == 200
    assert len(aippt_service.requests) == 1
    assert aippt_service.requests[0].page_count == 3
    assert "第 3 页：行动方案" in (aippt_service.requests[0].topic or "")


def test_agent_chat_current_ppt_regenerate_request_starts_new_generation_with_clarification() -> None:
    aippt_service = FakeAIPPTService()
    sync_service = RecordingSyncService(
        artifact={
            "kind": "ppt",
            "job_id": "aippt-old",
            "status": "done",
            "download_url": "/api/v1/ppt/files/aippt-old",
        }
    )
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "重新生成一个动漫发展ppt"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"] is None
    assert payload["plan"]["need_clarification"] is True
    assert "模板模式" in payload["message"]
    assert aippt_service.requests == []


def test_agent_chat_stream_current_ppt_regenerate_request_asks_mode_not_edit() -> None:
    aippt_service = FakeAIPPTService()
    sync_service = RecordingSyncService(
        artifact={
            "kind": "ppt",
            "job_id": "aippt-old",
            "status": "done",
            "download_url": "/api/v1/ppt/files/aippt-old",
        }
    )
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={"session_id": "s1", "message": "重新生成一个动漫发展ppt"},
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    names = event_names(events)
    assert "clarification.requested" in names
    assert "tool.started" not in names
    assert "ppt_edit" not in [event_payload(event).get("tool") for event in events]
    clarification = next(event for event in events if event["event"] == "clarification.requested")
    assert "模板模式" in clarification["message"]
    assert aippt_service.requests == []


def test_agent_chat_stream_current_ppt_edit_says_edit_not_create() -> None:
    aippt_service = FakeAIPPTService()
    sync_service = RecordingSyncService(
        artifact={
            "kind": "ppt",
            "job_id": "aippt-old",
            "status": "done",
            "download_url": "/api/v1/ppt/files/aippt-old",
        }
    )
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={"session_id": "s1", "message": "第一页文字全换掉，改成一句话：这是自测验证文字"},
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    assert events[1]["message"] == "我判断这次是修改当前 PPT，不会重新生成一份。"
    assert event_payload(events[2])["plan"]["intent"] == "ppt_editing"
    assert event_payload(events[-2])["tool"] == "ppt_edit"
    assert event_payload(events[-1])["response"]["intent"] == "ppt"
    assert "## 当前 PPT" in aippt_service.requests[0].topic


def test_agent_chat_stream_uses_fallback_plan_when_planner_is_slow() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=SlowPlannerLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={"session_id": "s1", "message": "用模板模式生成环保主题 ppt"},
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    names = event_names(events)
    assert event_payload(events[1])["intent"] == "ppt"
    assert "plan.step" in names
    assert names[-2:] == ["tool.started", "result.created"]
    assert event_payload(events[-1])["response"]["intent"] == "ppt"
    assert len(aippt_service.requests) == 1


def test_agent_chat_stream_unspecified_ppt_design_mode_stops_for_clarification() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=SlowPlannerLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
                json={"session_id": "s1", "message": "生成环保主题 ppt"},
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    names = event_names(events)
    assert "clarification.requested" in names
    assert "tool.started" not in names
    assert "result.created" not in names
    clarification = next(event for event in events if event["event"] == "clarification.requested")
    assert "模板模式" in clarification["message"]
    assert "自由设计" in clarification["message"]
    assert aippt_service.requests == []


def test_agent_chat_stream_ppt_mode_short_reply_continues_pending_generation() -> None:
    aippt_service = FakeAIPPTService()
    sync_service = RecordingSyncService(
        messages=[
            SyncSessionMessageSchema(role="user", content="生成一份2页PPT，主题是「客户成功月报」。"),
            SyncSessionMessageSchema(
                role="assistant",
                content="你希望用「模板模式」快速稳定生成，还是用「自由设计」做更强视觉表现？请回复“模板模式”或“自由设计”。",
            ),
            SyncSessionMessageSchema(role="user", content="模板"),
        ],
    )
    service = AgentService(
        llm_client=SlowPlannerLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={"session_id": "s1", "message": "模板"},
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    names = event_names(events)
    assert "clarification.requested" not in names
    assert event_payload(events[1])["intent"] == "ppt"
    assert event_payload(events[names.index("plan.created")])["plan"]["need_clarification"] is False
    assert event_payload(events[-2])["tool"] == "ppt"
    assert event_payload(events[-1])["response"]["artifact"]["kind"] == "ppt"
    assert aippt_service.requests[0].design_mode == "template"
    assert aippt_service.requests[0].page_count == 2
    assert "客户成功月报" in (aippt_service.requests[0].topic or "")


def test_agent_chat_stream_ppt_mode_short_reply_uses_request_chat_history() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=SlowPlannerLLMClient(intent="chat"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json={
                "session_id": "s1",
                "message": "模板",
                "context": {
                    "chat_history": [
                        {"role": "user", "content": "重新生成一份2页PPT，主题是「动画发展」。"},
                        {
                            "role": "assistant",
                            "content": "你希望用「模板模式」快速稳定生成，还是用「自由设计」做更强视觉表现？请回复“模板模式”或“自由设计”。",
                        },
                        {"role": "user", "content": "模板"},
                    ]
                },
            },
        ) as response:
            lines = list(response.iter_lines())

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in lines
        if line.startswith("data: ")
    ]
    assert "clarification.requested" not in event_names(events)
    assert event_payload(events[1])["intent"] == "ppt"
    assert event_payload(events[-2])["tool"] == "ppt"
    assert event_payload(events[-1])["response"]["artifact"]["kind"] == "ppt"
    assert aippt_service.requests[0].design_mode == "template"
    assert aippt_service.requests[0].page_count == 2
    assert "动画发展" in (aippt_service.requests[0].topic or "")


def test_agent_chat_uses_requested_ppt_page_count() -> None:
    aippt_service = FakeAIPPTService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "用模板模式生成一份 ppt 5 页 任意主题 测试用"},
        )

    assert response.status_code == 200
    assert aippt_service.requests[0].page_count == 5


def test_agent_chat_routes_board_to_feishu_board_pipeline() -> None:
    service = make_service("board")

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "把这个流程画到飞书画板",
                "sharing_url": "https://example.feishu.cn/wiki/board/wbcn123",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "board"
    assert payload["artifact"]["kind"] == "board"
    assert payload["artifact"]["task_id"] == "board-task-1"
    assert payload["artifact"]["status"] == "succeeded"
    assert payload["artifact"]["whiteboard_id"] == "wbcn123"
    assert payload["artifact"]["render_mode"] == "create_notes"
    assert payload["artifact"]["preview_url"] == "https://stub.preview/wbcn123.png"
    assert payload["artifact"]["ticket_id"] == "ticket-wbcn123"
    assert "tool.completed" in event_names(payload["events"])


def test_agent_chat_board_includes_rag_context_in_instruction() -> None:
    canvas_service = FakeCanvasService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="board"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=canvas_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "把星途智能业务布局画到飞书画板",
                "sharing_url": "https://example.feishu.cn/wiki/board/wbcn123",
                "context": {
                    "knowledge_docs": [
                        {
                            "title": "星途资料",
                            "content": "星途智能构建B端产业赋能与C端智能应用双向业务布局。",
                            "source": "rag-file",
                        }
                    ]
                },
            },
        )

    assert response.status_code == 200
    assert "## RAG 知识库资料" in canvas_service.created_messages[0]
    assert "B端产业赋能与C端智能应用双向业务布局" in canvas_service.created_messages[0]


def test_agent_chat_edits_current_board_without_creating_new_doc() -> None:
    canvas_service = FakeCanvasService()
    feishu_service = RecordingFeishuService()
    sync_service = RecordingSyncService(
        artifact={
            "kind": "board",
            "task_id": "board-old",
            "status": "succeeded",
            "sharing_url": "https://example.feishu.cn/wiki/board/current",
            "whiteboard_id": "wb-current",
        }
    )
    service = AgentService(
        llm_client=FakeLLMClient(intent="chat"),
        feishu_service=feishu_service,  # type: ignore[arg-type]
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=canvas_service,
        sync_service=sync_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "把第一个节点改成审批通过"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "board"
    assert payload["artifact"]["kind"] == "board"
    assert canvas_service.created_messages == ["把第一个节点改成审批通过"]
    assert canvas_service.created_sharing_urls == ["https://example.feishu.cn/wiki/board/current"]
    assert feishu_service.created_board_documents == []


def test_agent_chat_auto_creates_board_document_without_sharing_url() -> None:
    service = make_service("board")

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "把这个流程画到飞书画板",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "board"
    assert payload["status"] == "completed"
    assert payload["message"] == "飞书画板任务已完成。"
    assert payload["artifact"]["kind"] == "board"
    assert payload["artifact"]["status"] == "succeeded"
    assert payload["artifact"]["sharing_url"] == "https://example.feishu.cn/wiki/board/wbcn123"
    assert payload["artifact"]["result_summary"].startswith("已自动创建飞书文档并生成画板")


def test_agent_chat_shares_auto_created_board_doc_to_feishu_chat() -> None:
    feishu_service = RecordingFeishuService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="board"),
        feishu_service=feishu_service,  # type: ignore[arg-type]
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "feishu:oc_chat_1:om_msg_1", "message": "生成测试流程图"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "board"
    assert feishu_service.created_board_documents[0].startswith("Eko 画板")
    assert feishu_service.granted_permissions == [("docx_board_1", "oc_chat_1", "edit")]
    assert feishu_service.sent_messages == [
        (
            "oc_chat_1",
            "Eko 已创建飞书画板文档并完成生成：\n"
            "https://example.feishu.cn/docx/docx_board_1\n"
            "画板 ID：wbcn123",
        )
    ]


def test_agent_chat_routes_idea_map_to_board_not_docx() -> None:
    service = AgentService(
        llm_client=JsonBoardToolIntentLLMClient(),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "生成一个营销新产品的思路图吧"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "board"
    assert payload["artifact"]["kind"] == "board"


def test_agent_chat_includes_context_in_llm_prompt() -> None:
    llm = FakeLLMClient(intent="chat", reply="收到")
    service = AgentService(
        llm_client=llm,
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "message",
                "context": {
                    "chat_history": [
                        {"role": "user", "content": "前面在讨论排期"},
                        {"role": "eko", "content": "我建议先定里程碑"},
                    ]
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["message"] == "收到"
    assert llm.calls[-1][1].count("前面在讨论排期") == 1
    assert "飞书群聊上下文" in llm.calls[-1][1]


def test_agent_chat_publishes_sync_messages_intent_and_artifact() -> None:
    sync_service = RecordingSyncService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "用模板模式生成项目汇报 PPT",
                "context": {
                    "chat_history": [
                        {"role": "user", "content": "先按季度总结"},
                    ]
                },
            },
    )

    assert response.status_code == 200
    assert len(sync_service.completed) == 2

    started_payload = sync_service.completed[0]
    assert started_payload["intent"] == "ppt"
    assert started_payload["status"] == "进行中"
    assert started_payload["message"] == "AI PPT 任务已创建，正在后台生成。"
    assert started_payload["artifact"] == {
        "kind": "ppt",
        "content": None,
        "job_id": "aippt-job-1",
        "download_url": "/api/v1/ppt/files/aippt-job-1",
        "progress": 0,
        "current_step": "任务已入队",
        "task_id": None,
        "status": "queued",
        "whiteboard_id": None,
        "sharing_url": None,
        "result_summary": None,
        "error_message": None,
    }
    assert started_payload["messages"] == [
        {"role": "user", "content": "用模板模式生成项目汇报 PPT"},
        {"role": "assistant", "content": "AI PPT 任务已创建，正在后台生成。"},
    ]

    completed_payload = sync_service.completed[1]
    assert completed_payload["intent"] == "ppt"
    assert completed_payload["status"] == "completed"
    assert completed_payload["message"] == "AI PPT 已生成。"
    assert completed_payload["artifact"] == {
        "kind": "ppt",
        "content": None,
        "job_id": "aippt-job-1",
        "download_url": "/api/v1/ppt/files/aippt-job-1",
        "progress": 100,
        "current_step": "导出完成",
        "task_id": None,
        "status": "done",
        "whiteboard_id": None,
        "sharing_url": None,
        "result_summary": None,
        "error_message": None,
    }
    assert completed_payload["messages"] == [
        {"role": "user", "content": "用模板模式生成项目汇报 PPT"},
        {"role": "assistant", "content": "AI PPT 已生成。"},
    ]


def test_agent_chat_syncs_completed_ppt_to_feishu_document_share_link() -> None:
    sync_service = RecordingSyncService()
    feishu_service = RecordingFeishuService()
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=feishu_service,  # type: ignore[arg-type]
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "feishu:oc_chat_1:om_msg_1", "message": "用模板模式生成项目汇报 PPT"},
        )

    assert response.status_code == 200
    assert len(sync_service.completed) == 2
    completed_payload = sync_service.completed[-1]
    assert completed_payload["message"] == "AI PPT 已生成，并已同步到飞书文档。"
    assert completed_payload["artifact"]["sharing_url"] == "https://example.feishu.cn/docx/docx_doc_1"
    assert completed_payload["messages"] == [
        {"role": "user", "content": "用模板模式生成项目汇报 PPT"},
        {"role": "assistant", "content": "AI PPT 已生成，并已同步到飞书文档。"},
    ]
    assert feishu_service.granted_permissions == [("docx_doc_1", "oc_chat_1", "edit")]
    assert feishu_service.sent_messages == [
        ("oc_chat_1", "Eko 已创建飞书 PPT 分享文档：\nhttps://example.feishu.cn/docx/docx_doc_1")
    ]
    title, markdown = feishu_service.published_markdown[0]
    assert title.startswith("Eko PPT")
    assert "下载 PPT：http://127.0.0.1:8000/api/v1/ppt/files/aippt-job-1" in markdown
    assert "## 幻灯片目录" in markdown
    assert "### 第 1 页：封面" in markdown


def test_agent_chat_sync_message_merge_collapses_repeated_current_turn_progress() -> None:
    sync_service = RecordingSyncService(
        messages=[
            {"role": "user", "content": "生成中国蛋糕行业的报告", "sender_open_id": "ou_1"},
            {"role": "assistant", "content": "收到。我先理解你的任务，并拆成可以执行的步骤。"},
            {"role": "assistant", "content": "收到。我先理解你的任务，并拆成可以执行的步骤。\n\n我判断这次要走 docx 能力。"},
            {"role": "user", "content": "生成中国蛋糕行业的报告", "sender_open_id": "ou_1"},
            {"role": "assistant", "content": "收到。我先理解你的任务，并拆成可以执行的步骤。\n\n好的，我现在调用文档生成能力。"},
        ]
    )
    service = AgentService(
        llm_client=FakeLLMClient(),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    messages = asyncio.run(
        service._build_merged_sync_messages(
            AgentChatRequest(
                session_id="s1",
                message="生成中国蛋糕行业的报告",
                sender={"sender_open_id": "ou_1"},
            ),
            AgentChatResponse(
                session_id="s1",
                intent="docx",
                status="completed",
                message="文档生成完成，并已同步到飞书。",
            ),
        )
    )

    assert messages == [
        {"role": "user", "content": "生成中国蛋糕行业的报告", "sender_open_id": "ou_1"},
        {"role": "assistant", "content": "文档生成完成，并已同步到飞书。"},
    ]


def test_agent_chat_publishes_failed_ppt_sync_update_after_background_generation() -> None:
    sync_service = RecordingSyncService()
    aippt_service = FakeAIPPTService()
    aippt_service.final_status = "failed"
    aippt_service.final_step = "任务失败"
    aippt_service.final_download_url = None
    aippt_service.final_error = "deck render failed"
    service = AgentService(
        llm_client=FakeLLMClient(intent="ppt"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=aippt_service,
        canvas_service=FakeCanvasService(),
        sync_service=sync_service,
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "用模板模式生成项目汇报 PPT"},
        )

    assert response.status_code == 200
    assert len(sync_service.completed) == 2

    failed_payload = sync_service.completed[-1]
    assert failed_payload["intent"] == "ppt"
    assert failed_payload["status"] == "failed"
    assert failed_payload["message"] == "AI PPT 生成失败，请稍后重试。"
    assert failed_payload["error"] == "deck render failed"
    assert failed_payload["artifact"] == {
        "kind": "ppt",
        "content": None,
        "job_id": "aippt-job-1",
        "download_url": None,
        "progress": 100,
        "current_step": "任务失败",
        "task_id": None,
        "status": "failed",
        "whiteboard_id": None,
        "sharing_url": None,
        "result_summary": None,
        "error_message": "deck render failed",
    }
    assert failed_payload["messages"] == [
        {"role": "user", "content": "用模板模式生成项目汇报 PPT"},
        {"role": "assistant", "content": "AI PPT 生成失败，请稍后重试。: deck render failed"},
    ]


def test_agent_chat_preserves_failed_board_task_status() -> None:
    service = AgentService(
        llm_client=FakeLLMClient(intent="board"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FailingCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "把这个流程画到飞书画板",
                "sharing_url": "https://example.feishu.cn/wiki/board/wbcn123",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "board"
    assert payload["status"] == "failed"
    assert payload["artifact"]["status"] == "failed"
    assert payload["artifact"]["error_message"] == "Feishu board request failed"


def test_agent_chat_uses_board_heuristic_when_llm_classification_fails() -> None:
    service = AgentService(
        llm_client=FailingIntentLLMClient(reply="不会走到这里"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "把这个流程画到飞书画板",
                "sharing_url": "https://example.feishu.cn/wiki/board/wbcn123",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "board"
    assert payload["status"] == "completed"
    assert payload["artifact"]["kind"] == "board"


def test_agent_chat_routes_architecture_diagram_to_board_heuristic_when_llm_classification_fails() -> None:
    service = AgentService(
        llm_client=FailingIntentLLMClient(reply="不会走到这里"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "session_id": "s1",
                "message": "帮我画一个 AI 网关架构图",
                "sharing_url": "https://example.feishu.cn/wiki/board/wbcn123",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "board"
    assert payload["status"] == "completed"
    assert payload["artifact"]["kind"] == "board"


def test_agent_chat_uses_docx_heuristic_when_llm_classification_is_empty() -> None:
    service = AgentService(
        llm_client=EmptyIntentLLMClient(reply="不会走到这里"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "写一份项目总结文档"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "docx"
    assert payload["status"] == "completed"
    assert payload["artifact"]["kind"] == "docx"


def test_agent_chat_uses_ppt_heuristic_when_llm_classification_fails() -> None:
    service = AgentService(
        llm_client=FailingIntentLLMClient(reply="不会走到这里"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "帮我用模板模式生成一份项目汇报PPT"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["status"] == "completed"
    assert payload["artifact"]["kind"] == "ppt"


def test_agent_chat_uses_structured_model_intent_response() -> None:
    service = AgentService(
        llm_client=JsonIntentLLMClient(reply="不会走到这里"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        aippt_service=FakeAIPPTService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "帮我用模板模式整理成给老师看的项目展示材料"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"]["job_id"] == "aippt-job-1"
