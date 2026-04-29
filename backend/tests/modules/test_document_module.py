from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.llm_client import LLMRequestError
from app.modules.document import router as document_router_module
from app.modules.document.dependencies import get_document_service
from app.modules.document.schemas import DocumentGenerationRequest
from app.modules.document.service import DocumentService


class FakeLLMClient:
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "# generated"

    async def generate_stream(self, system_prompt: str, user_prompt: str):
        for chunk in ['He said "hi"\n', "next line"]:
            yield chunk


class RecordingFeishuService:
    def __init__(self, *, result: dict | None = None, error: Exception | None = None) -> None:
        self.calls: list[dict[str, str | None]] = []
        self._result = result or {
            "ticket": "ticket-1",
            "document_url": "https://feishu.cn/doc/1",
            "record_id": "record-1",
            "status": "success",
        }
        self._error = error

    async def publish_markdown_to_feishu(
        self,
        title: str,
        markdown_content: str,
        app_token: str | None = None,
        table_id: str | None = None,
    ) -> dict:
        self.calls.append(
            {
                "title": title,
                "markdown_content": markdown_content,
                "app_token": app_token,
                "table_id": table_id,
            }
        )
        if self._error is not None:
            raise self._error
        return self._result


class RecordingRedisClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> None:
        self.messages.append((channel, message))


class FailingLLMClient:
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise LLMRequestError(
            status_code=403,
            message="AccessDenied: upstream blocked the request",
        )

    async def generate_stream(self, system_prompt: str, user_prompt: str):
        raise LLMRequestError(
            status_code=403,
            message="AccessDenied: upstream blocked the request",
        )
        yield  # pragma: no cover


def _build_document_request() -> DocumentGenerationRequest:
    return DocumentGenerationRequest(
        session_id="session-1",
        topic="topic",
        requirement="requirement",
    )


def test_stream_endpoint_emits_valid_json_events() -> None:
    app = FastAPI()
    app.include_router(document_router_module.router, prefix="/api/v1/document")
    app.dependency_overrides[get_document_service] = lambda: DocumentService(
        llm_client=FakeLLMClient(),
        feishu_service=RecordingFeishuService(),
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/document/generate/stream",
            json=_build_document_request().model_dump(mode="json"),
        ) as response:
            assert response.status_code == 200
            lines = [
                line for line in response.iter_lines()
                if line and line.startswith("data: ")
            ]

    payloads = [json.loads(line[6:]) for line in lines]
    assert payloads == [
        {"session_id": "session-1", "status": "generating"},
        {"content": 'He said "hi"\n'},
        {"content": "next line"},
        {"status": "completed"},
    ]


def test_generate_endpoint_returns_json_error_for_upstream_rejection() -> None:
    app = FastAPI()
    app.include_router(document_router_module.router, prefix="/api/v1/document")
    app.dependency_overrides[get_document_service] = lambda: DocumentService(
        llm_client=FailingLLMClient(),
        feishu_service=RecordingFeishuService(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/document/generate",
            json=_build_document_request().model_dump(mode="json"),
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "LLM service rejected the request: AccessDenied: upstream blocked the request"
    }


def test_stream_endpoint_emits_failed_event_for_upstream_rejection() -> None:
    app = FastAPI()
    app.include_router(document_router_module.router, prefix="/api/v1/document")
    app.dependency_overrides[get_document_service] = lambda: DocumentService(
        llm_client=FailingLLMClient(),
        feishu_service=RecordingFeishuService(),
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/document/generate/stream",
            json=_build_document_request().model_dump(mode="json"),
        ) as response:
            assert response.status_code == 200
            lines = [
                line for line in response.iter_lines()
                if line and line.startswith("data: ")
            ]

    payloads = [json.loads(line[6:]) for line in lines]
    assert payloads == [
        {"session_id": "session-1", "status": "generating"},
        {
            "status": "failed",
            "error": "LLM service rejected the request: AccessDenied: upstream blocked the request",
        },
    ]


def test_save_and_sync_document_publishes_success_status() -> None:
    redis_client = RecordingRedisClient()
    feishu_service = RecordingFeishuService(
        result={
            "ticket": "ticket-1",
            "document_url": "https://feishu.cn/doc/success",
            "record_id": "record-1",
            "status": "success",
        }
    )
    service = DocumentService(
        llm_client=FakeLLMClient(),
        feishu_service=feishu_service,
        redis_client=redis_client,
    )

    result = asyncio.run(
        service.save_and_sync_document(
            session_id="session-1",
            title="Weekly Report",
            content="# content",
            app_token="app-token",
            table_id="table-id",
        )
    )

    assert feishu_service.calls == [
        {
            "title": "Weekly Report",
            "markdown_content": "# content",
            "app_token": "app-token",
            "table_id": "table-id",
        }
    ]
    assert result == {
        "session_id": "session-1",
        "status": "completed",
        "document_url": "https://feishu.cn/doc/success",
        "record_id": "record-1",
    }
    assert redis_client.messages == [
        (
            "eko:document:sync:session-1",
            json.dumps(
                {
                    "session_id": "session-1",
                    "status": "completed",
                    "document_url": "https://feishu.cn/doc/success",
                    "record_id": "record-1",
                }
            ),
        )
    ]


def test_save_and_sync_document_publishes_failed_status() -> None:
    redis_client = RecordingRedisClient()
    service = DocumentService(
        llm_client=FakeLLMClient(),
        feishu_service=RecordingFeishuService(error=RuntimeError("import failed")),
        redis_client=redis_client,
    )

    result = asyncio.run(
        service.save_and_sync_document(
            session_id="session-2",
            title="Broken Report",
            content="# broken",
        )
    )

    assert result == {
        "session_id": "session-2",
        "status": "failed",
        "document_url": None,
        "record_id": None,
        "error": "import failed",
    }
    assert redis_client.messages == [
        (
            "eko:document:sync:session-2",
            json.dumps(
                {
                    "session_id": "session-2",
                    "status": "failed",
                    "document_url": None,
                    "record_id": None,
                    "error": "import failed",
                }
            ),
        )
    ]
