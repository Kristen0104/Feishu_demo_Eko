from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.llm_client import LLMRequestError
from app.modules.document import router as document_router_module
from app.modules.document.dependencies import get_document_service
from app.modules.document.schemas import DocumentAutoSyncRequest, DocumentGenerationRequest
from app.modules.document.service import DocumentService
from app.modules.sync.dependencies import get_sync_service


class FakeLLMClient:
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "# generated"

    async def generate_stream(self, system_prompt: str, user_prompt: str):
        for chunk in ['He said "hi"\n', "next line"]:
            yield chunk


class PromptRecordingLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return "# generated"


class RecordingFeishuService:
    def __init__(self, *, result: dict | None = None, error: Exception | None = None) -> None:
        self.calls: list[dict[str, str | None]] = []
        self.permission_calls: list[dict[str, str]] = []
        self.chat_messages: list[dict[str, str]] = []
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

    async def add_docx_permission_for_chat(
        self,
        document_id: str,
        chat_id: str,
        *,
        perm: str = "edit",
    ) -> dict:
        self.permission_calls.append({"document_id": document_id, "chat_id": chat_id, "perm": perm})
        return {"member_id": chat_id, "perm": perm}

    async def send_text_message_to_chat(self, chat_id: str, text: str) -> dict:
        self.chat_messages.append({"chat_id": chat_id, "text": text})
        return {"message_id": "message-1"}


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


class RecordingSyncService:
    def __init__(self) -> None:
        self.completed: list[dict] = []

    async def publish_task_completed(self, session_id: str, **kwargs) -> None:
        self.completed.append({"session_id": session_id, **kwargs})


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


def test_document_generation_prompt_requires_rag_factual_grounding() -> None:
    llm = PromptRecordingLLMClient()
    service = DocumentService(llm_client=llm, feishu_service=RecordingFeishuService())

    asyncio.run(
        service.generate_document(
            DocumentGenerationRequest(
                session_id="s1",
                topic="生成公司介绍",
                requirement="必须包含总部和研发中心",
                knowledge_docs=[
                    {
                        "title": "星途资料",
                        "content": "总部坐落于北京海淀，在深圳、杭州设有两大研发及产业赋能中心。",
                        "source": "rag-file",
                    }
                ],
            )
        )
    )

    prompt = llm.calls[-1][1]
    assert "不得新增、替换或编造" in prompt
    assert "RAG 原文关键事实" in prompt
    assert "北京海淀" in prompt
    assert "深圳、杭州" in prompt


class HallucinatingLocationLLMClient(FakeLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "# 公司介绍\n\n总部位于上海市，在北京市设有研发中心。"


class GenericBusinessModelLLMClient(FakeLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return """
# 公司商业模式概括

## 价值主张
我们致力于为现代企业与团队提供高效、智能、一体化的办公协作解决方案。

## 核心业务与产品
- 智能办公平台
- 即时通讯
- 智能日历
- 审批流自动化
- 项目任务管理
- RPA（机器人流程自动化）
- 应用市场
"""


def test_document_generation_falls_back_when_rag_facts_are_not_grounded() -> None:
    service = DocumentService(
        llm_client=HallucinatingLocationLLMClient(),
        feishu_service=RecordingFeishuService(),
    )

    content = asyncio.run(
        service.generate_document(
            DocumentGenerationRequest(
                session_id="s1",
                topic="星途智能公司介绍",
                requirement="必须包含总部、研发中心、星枢大模型、B端和C端业务布局",
                knowledge_docs=[
                    {
                        "title": "星途资料",
                        "content": (
                            "星途智能科技有限公司总部坐落于北京海淀人工智能产业核心集聚区，"
                            "在深圳、杭州设有两大研发及产业赋能中心。"
                            "星途智能核心自研“星枢”系列通用认知大模型。"
                            "目前，公司依托核心大模型技术，构建B端产业赋能与C端智能应用双向业务布局。"
                        ),
                        "source": "rag-file",
                    }
                ],
            )
        )
    )

    assert "上海市" not in content
    assert "总部坐落于北京海淀人工智能产业核心集聚区" in content
    assert "在深圳、杭州设有两大研发及产业赋能中心" in content
    assert "星枢" in content
    assert "B端产业赋能与C端智能应用双向业务布局" in content


def test_document_generation_falls_back_when_business_model_ignores_rag() -> None:
    service = DocumentService(
        llm_client=GenericBusinessModelLLMClient(),
        feishu_service=RecordingFeishuService(),
    )

    content = asyncio.run(
        service.generate_document(
            DocumentGenerationRequest(
                session_id="s1",
                topic="生成公司的商业模式概括",
                requirement="生成公司的商业模式概括",
                knowledge_docs=[
                    {
                        "title": "星途智能AI大模型公司 商业模式与战略合作专项文档",
                        "content": (
                            "星途智能整体采用核心技术自研+模型服务输出+行业定制交付+生态渠道联营的一体化商业模式。"
                            "公司核心营收来源聚焦三大板块，分别为大模型基础算力与云端调用服务、"
                            "政企行业定制化AI智能化改造项目、轻量化终端模型授权及长期运维增值服务。"
                            "公司战略合作生态合作分为渠道合作伙伴、行业解决方案伙伴、算力硬件配套伙伴三大类别。"
                        ),
                        "source": "rag-file",
                    }
                ],
            )
        )
    )

    assert "智能办公平台" not in content
    assert "星途智能整体采用核心技术自研" in content
    assert "三大板块" in content
    assert "云端调用服务" in content
    assert "政企行业定制化AI智能化改造项目" in content
    assert "轻量化终端模型授权" in content
    assert "渠道合作伙伴、行业解决方案伙伴、算力硬件配套伙伴" in content


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


def test_auto_sync_markdown_document_publishes_without_llm_grants_chat_edit_without_chat_spam() -> None:
    feishu_service = RecordingFeishuService(
        result={
            "ticket": "ticket-1",
            "document_url": "https://example.feishu.cn/docx/doc-token",
            "record_id": "record-1",
            "status": "success",
        }
    )
    service = DocumentService(
        llm_client=FakeLLMClient(),
        feishu_service=feishu_service,
    )

    result = asyncio.run(
        service.auto_sync_markdown_document(
            DocumentAutoSyncRequest(
                session_id="feishu:chat-1:msg-1",
                title="客户续费方案",
                content="# 已手动编辑",
            )
        )
    )

    assert result["status"] == "completed"
    assert result["document_url"] == "https://example.feishu.cn/docx/doc-token"
    assert feishu_service.calls == [
        {
            "title": "客户续费方案",
            "markdown_content": "# 已手动编辑",
            "app_token": None,
            "table_id": None,
        }
    ]
    assert feishu_service.permission_calls == [
        {"document_id": "doc-token", "chat_id": "chat-1", "perm": "edit"}
    ]
    assert feishu_service.chat_messages == []


def test_auto_sync_endpoint_updates_sync_session_artifact() -> None:
    app = FastAPI()
    app.include_router(document_router_module.router, prefix="/api/v1/document")
    sync_service = RecordingSyncService()
    app.dependency_overrides[get_document_service] = lambda: DocumentService(
        llm_client=FakeLLMClient(),
        feishu_service=RecordingFeishuService(
            result={
                "ticket": "ticket-1",
                "document_url": "https://example.feishu.cn/docx/synced",
                "record_id": "record-1",
                "status": "success",
            }
        ),
    )
    app.dependency_overrides[get_sync_service] = lambda: sync_service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/document/sync",
            json={
                "session_id": "session-1",
                "title": "手动编辑文档",
                "content": "# 手动内容",
                "current_url": "https://old.example/docx/old",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "session_id": "session-1",
        "status": "completed",
        "message": "文档已自动同步到飞书。",
        "document_url": "https://example.feishu.cn/docx/synced",
    }
    assert sync_service.completed == [
        {
            "session_id": "session-1",
            "intent": "docx",
            "message": "文档已自动同步到飞书。",
            "status": "completed",
            "artifact": {
                "kind": "docx",
                "content": "# 手动内容",
                "status": "completed",
                "current_step": "文档已自动同步",
                "sharing_url": "https://example.feishu.cn/docx/synced",
                "result_summary": "文档已自动同步到飞书。",
            },
            "messages": None,
            "error": None,
        }
    ]
