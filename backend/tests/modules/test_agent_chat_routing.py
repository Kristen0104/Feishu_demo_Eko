from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.agent.dependencies import get_agent_service
from app.modules.agent.router import router as agent_router
from app.modules.agent.service import AgentService
from app.modules.canvas.schemas import CanvasBoardTaskSchema
from app.modules.document.schemas import DocumentGenerationRequest
from app.modules.feishu.service import FeishuService
from app.modules.ppt.schemas import PptDeckCreateRequest, PptDeckSchema, PptPreferencesSchema, PptSlideSchema


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


class FakeDocumentService:
    def __init__(self) -> None:
        self.requests: list[DocumentGenerationRequest] = []

    async def generate_document(self, request: DocumentGenerationRequest) -> str:
        self.requests.append(request)
        return "# 方案\n\n文档内容"


class FakePptService:
    def __init__(self) -> None:
        self.requests: list[PptDeckCreateRequest] = []

    def create_deck(self, payload: PptDeckCreateRequest) -> PptDeckSchema:
        self.requests.append(payload)
        return PptDeckSchema(
            deck_id="deck-1",
            type=payload.type,
            title="汇报 PPT",
            source_content=payload.content,
            theme=payload.preferences.theme,
            last_modified="2026-04-29T00:00:00+00:00",
            slides=[
                PptSlideSchema(
                    slide_id="slide-1",
                    layout="cover",
                    title="汇报 PPT",
                    body=[],
                )
            ],
            html="<html></html>",
        )


class FakeCanvasService:
    def __init__(self) -> None:
        self.created_messages: list[str] = []
        self.run_task_ids: list[str] = []

    def create_board_task(self, payload):
        self.created_messages.append(payload.message)
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


def build_client(service: AgentService) -> TestClient:
    app = FastAPI()
    app.include_router(agent_router, prefix="/api/v1/agent")
    app.dependency_overrides[get_agent_service] = lambda: service
    return TestClient(app)


def make_service(intent: str, reply: str = "你好，我是 Eko。") -> AgentService:
    return AgentService(
        llm_client=FakeLLMClient(intent=intent, reply=reply),
        feishu_service=FeishuService(client=None),  # not used by these routed paths
        document_service=FakeDocumentService(),
        ppt_service=FakePptService(),
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


def test_agent_chat_routes_ppt_to_ppt_service() -> None:
    service = make_service("ppt")

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "生成项目汇报 PPT"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["artifact"]["kind"] == "ppt"
    assert payload["artifact"]["deck_id"] == "deck-1"


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


def test_agent_chat_returns_failed_board_response_without_sharing_url() -> None:
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
    assert payload["status"] == "failed"
    assert payload["error"] == "missing sharing_url"


def test_agent_chat_preserves_failed_board_task_status() -> None:
    service = AgentService(
        llm_client=FakeLLMClient(intent="board"),
        feishu_service=FeishuService(client=None),
        document_service=FakeDocumentService(),
        ppt_service=FakePptService(),
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
        ppt_service=FakePptService(),
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
        ppt_service=FakePptService(),
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
        ppt_service=FakePptService(),
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
        ppt_service=FakePptService(),
        canvas_service=FakeCanvasService(),
    )

    with build_client(service) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "帮我生成一份项目汇报PPT"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["intent"] == "ppt"
    assert payload["status"] == "completed"
    assert payload["artifact"]["kind"] == "ppt"
