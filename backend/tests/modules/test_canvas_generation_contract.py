from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from app.core import container
from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.ai_service import HttpCanvasAiService
from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import BoardPatchSchema
from app.modules.canvas.schemas import BoardChangeSchema
from app.modules.canvas.schemas import CanvasGenerationRequestSchema
from app.modules.canvas.service import CanvasService
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
    FeishuBoardSourceSchema,
    FeishuDocumentContentSchema,
)


def _build_client(canvas_service: CanvasService | None = None) -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    test_canvas_service = canvas_service or CanvasService(repository=CanvasRepository())
    app.dependency_overrides[get_canvas_service] = lambda: test_canvas_service
    return TestClient(app)


class StubCanvasAiService:
    def __init__(self, patch: BoardPatchSchema | None = None, error: Exception | None = None) -> None:
        self.patch = patch
        self.error = error

    def generate_patch(self, *, session_id: str, payload) -> BoardPatchSchema | None:
        if self.error is not None:
            raise self.error
        return self.patch


class RecordingHttpClient:
    def __init__(self) -> None:
        self.calls = []

    def post(self, url, headers, json):
        self.calls.append({"url": url, "headers": headers, "json": json})

        class Response:
            def raise_for_status(self_inner):
                return None

            def json(self_inner):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"generation_mode":"targeted_patch","patch_id":"canvas-provider-test-patch","operations":[{"type":"node.replace","target":"node-1","content":"来自火山"}],"summary":"volcengine","full_board":null,"targeted_patch":{"selection":{"selectedNodeIds":["node-1"]},"operations":[{"type":"node.replace","target":"node-1","content":"来自火山"}]}}'
                            }
                        }
                    ]
                }

        return Response()


def test_generate_canvas_patch_requires_ai_provider() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-001/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [{"role": "user", "content": "整理本周项目讨论"}],
            "user_prompt": "生成产品路线图画板",
            "board_context": {},
            "session_metadata": {"request_id": "gen-request-001"},
            "selection_context": None,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "Canvas AI provider is not configured"


def test_generate_canvas_patch_returns_full_board_from_ai_service() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="full_board",
        patch_id="canvas-flow-001-patch-llm",
        operations=[],
        summary="生成吃饭流程图",
        full_board={
            "nodes": [
                {
                    "id": "meal-select",
                    "type": "topic",
                    "text": "选餐",
                    "x": 120,
                    "y": 140,
                    "width": 220,
                    "height": 100,
                },
                {
                    "id": "meal-eat",
                    "type": "note",
                    "text": "用餐",
                    "x": 400,
                    "y": 140,
                    "width": 220,
                    "height": 100,
                },
            ],
            "edges": [
                {
                    "id": "meal-edge-1",
                    "from": "meal-select",
                    "to": "meal-eat",
                    "type": "association",
                }
            ],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        },
        targeted_patch=None,
        generation_info={"source": "ai", "provider": "test", "model": "test-model"},
    )
    client = _build_client(
        CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-flow-001/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成一个吃饭流程图",
            "board_context": {},
            "session_metadata": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    node_texts = [node["text"] for node in payload["full_board"]["nodes"]]
    assert node_texts == ["选餐", "用餐"]
    assert payload["generation_info"]["source"] == "ai"


def test_generate_canvas_patch_applies_style_template_before_returning_patch() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="full_board",
        patch_id="canvas-provider-style-patch",
        operations=[],
        summary="AI generated board",
        full_board={
            "nodes": [
                {"id": "start", "type": "topic", "text": "开始"},
                {
                    "id": "decision",
                    "type": "note",
                    "text": "是否继续?",
                    "shape_kind": "flow_chart_diamond",
                },
                {"id": "end", "type": "topic", "text": "结束"},
            ],
            "edges": [{"id": "edge-1", "from": "start", "to": "decision"}],
        },
    )
    client = _build_client(
        CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-provider-style/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成带模板样式的流程图",
            "board_context": {},
            "session_metadata": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    patch = response.json()["data"]
    nodes = {node["id"]: node for node in patch["full_board"]["nodes"]}
    assert nodes["start"]["style"]["border_color"] == "#16a34a"
    assert nodes["decision"]["style"]["border_color"] == "#f59e0b"
    assert nodes["end"]["style"]["border_color"] == "#4f46e5"
    assert patch["full_board"]["edges"][0]["arrow_style"] == "triangle_arrow"


def test_generate_canvas_patch_style_template_overrides_ai_color_choices() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="full_board",
        patch_id="canvas-provider-style-override-patch",
        operations=[],
        summary="AI generated board",
        full_board={
            "nodes": [
                {
                    "id": "start",
                    "type": "topic",
                    "text": "开始",
                    "style": {
                        "fill_color": "#e1eaff",
                        "border_color": "#4e83fd",
                    },
                }
            ],
            "edges": [],
        },
    )
    client = _build_client(
        CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-provider-style-override/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成带模板样式的流程图",
            "board_context": {},
            "session_metadata": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    node = response.json()["data"]["full_board"]["nodes"][0]
    assert node["style"]["fill_color"] == "#e7f8ef"
    assert node["style"]["border_color"] == "#16a34a"


def test_generate_canvas_patch_uses_ai_selected_style_plan() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="full_board",
        patch_id="canvas-provider-style-plan-patch",
        operations=[],
        summary="AI generated board",
        style_plan={"template": "sunset_flow"},
        full_board={
            "nodes": [
                {"id": "start", "type": "topic", "text": "开始"},
                {
                    "id": "step",
                    "type": "note",
                    "text": "执行步骤",
                },
                {"id": "end", "type": "topic", "text": "结束"},
            ],
            "edges": [{"id": "edge-1", "from": "start", "to": "step"}],
        },
    )
    client = _build_client(
        CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-provider-style-plan/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成一个暖色故事感流程图",
            "board_context": {},
            "session_metadata": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    patch = response.json()["data"]
    nodes = {node["id"]: node for node in patch["full_board"]["nodes"]}
    assert patch["style_plan"]["template"] == "sunset_flow"
    assert nodes["start"]["style"]["border_color"] == "#f97316"
    assert nodes["step"]["style"]["border_color"] == "#e11d48"
    assert nodes["end"]["style"]["border_color"] == "#dc2626"


def test_generate_canvas_patch_supports_more_ai_selected_style_plans() -> None:
    for template, expected_start, expected_step in [
        ("forest_flow", "#059669", "#0f766e"),
        ("mono_exec", "#475569", "#2563eb"),
    ]:
        ai_patch = BoardPatchSchema(
            generation_mode="full_board",
            patch_id=f"canvas-provider-{template}-patch",
            operations=[],
            summary="AI generated board",
            style_plan={"template": template},
            full_board={
                "nodes": [
                    {"id": "start", "type": "topic", "text": "开始"},
                    {"id": "step", "type": "note", "text": "执行步骤"},
                ],
                "edges": [{"id": "edge-1", "from": "start", "to": "step"}],
            },
        )
        client = _build_client(
            CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
        )

        response = client.post(
            f"/api/v1/canvas/sessions/canvas-provider-{template}/generate",
            json={
                "generation_mode": "full_board",
                "chat_context": [],
                "user_prompt": "生成一个流程图",
                "board_context": {},
                "session_metadata": {},
                "selection_context": None,
            },
        )

        assert response.status_code == 200
        patch = response.json()["data"]
        nodes = {node["id"]: node for node in patch["full_board"]["nodes"]}
        assert patch["style_plan"]["template"] == template
        assert nodes["start"]["style"]["border_color"] == expected_start
        assert nodes["step"]["style"]["border_color"] == expected_step


def test_generate_canvas_patch_preserves_branch_and_return_edges() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="full_board",
        patch_id="canvas-provider-branch-patch",
        operations=[],
        summary="AI generated branched board",
        style_plan={"template": "forest_flow"},
        full_board={
            "nodes": [
                {"id": "start", "type": "topic", "text": "开始"},
                {"id": "check", "type": "note", "text": "是否准备好?", "visual_role": "decision"},
                {"id": "do", "type": "note", "text": "执行"},
                {"id": "retry", "type": "note", "text": "补充准备"},
                {"id": "end", "type": "topic", "text": "结束"},
            ],
            "edges": [
                {"id": "edge-1", "from": "start", "to": "check"},
                {"id": "edge-2", "from": "check", "to": "do", "label": "是"},
                {"id": "edge-3", "from": "check", "to": "retry", "label": "否"},
                {"id": "edge-4", "from": "retry", "to": "check", "label": "返回"},
                {"id": "edge-5", "from": "do", "to": "end"},
            ],
        },
    )
    client = _build_client(
        CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-provider-branch/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成一个带 if else 和返回重试的流程图",
            "board_context": {},
            "session_metadata": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    patch = response.json()["data"]
    nodes = {node["id"]: node for node in patch["full_board"]["nodes"]}
    edges = {edge["id"]: edge for edge in patch["full_board"]["edges"]}
    assert nodes["check"]["shape_kind"] == "flow_chart_diamond"
    assert nodes["retry"]["style"]["border_width"] == "medium"
    assert edges["edge-3"]["from"] == "check"
    assert edges["edge-3"]["to"] == "retry"
    assert edges["edge-3"]["label"] == "否"
    assert edges["edge-4"]["from"] == "retry"
    assert edges["edge-4"]["to"] == "check"
    assert edges["edge-4"]["label"] == "返回"


def test_generate_canvas_patch_style_template_infers_start_and_end_from_long_text() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="full_board",
        patch_id="canvas-provider-style-long-text-patch",
        operations=[],
        summary="AI generated board",
        full_board={
            "nodes": [
                {"id": "start", "type": "topic", "text": "开始吃饭流程"},
                {"id": "end", "type": "topic", "text": "吃饭流程结束"},
            ],
            "edges": [],
        },
    )
    client = _build_client(
        CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-provider-style-long-text/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成吃饭流程",
            "board_context": {},
            "session_metadata": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    nodes = {node["id"]: node for node in response.json()["data"]["full_board"]["nodes"]}
    assert nodes["start"]["visual_role"] == "start"
    assert nodes["start"]["shape_kind"] == "state_start"
    assert nodes["end"]["visual_role"] == "end"
    assert nodes["end"]["shape_kind"] == "state_end"


def test_generate_canvas_patch_reflows_wide_linear_board_from_ai_service() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="full_board",
        patch_id="canvas-wide-001-patch-llm",
        operations=[],
        summary="生成长流程",
        full_board={
            "nodes": [
                {"id": f"step-{index}", "type": "note", "text": f"步骤 {index}", "x": 120 + (index - 1) * 260, "y": 150, "width": 200, "height": 80}
                for index in range(1, 7)
            ],
            "edges": [
                {"id": f"edge-{index}", "from": f"step-{index}", "to": f"step-{index + 1}", "type": "association"}
                for index in range(1, 6)
            ],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        },
        targeted_patch=None,
        generation_info={"source": "ai", "provider": "test", "model": "test-model"},
    )
    client = _build_client(
        CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-wide-001/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成一个很长的流程图",
            "board_context": {},
            "session_metadata": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    nodes = response.json()["data"]["full_board"]["nodes"]
    assert [nodes[i]["x"] for i in range(4)] == [120, 400, 680, 960]
    assert nodes[4]["x"] == 960
    assert nodes[4]["y"] == 320
    assert nodes[5]["x"] == 680


def test_generate_canvas_patch_reflows_multi_row_linear_board_even_when_not_ultra_wide() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="full_board",
        patch_id="canvas-multirow-001-patch-llm",
        operations=[],
        summary="生成两排流程",
        full_board={
            "nodes": [
                {
                    "id": f"step-{index}",
                    "type": "note",
                    "text": f"步骤 {index}",
                    "x": 120 + ((index - 1) % 5) * 270,
                    "y": 150 + ((index - 1) // 5) * 170,
                    "width": 220,
                    "height": 100,
                }
                for index in range(1, 11)
            ],
            "edges": [
                {
                    "id": f"edge-{index}",
                    "from": f"step-{index}",
                    "to": f"step-{index + 1}",
                    "type": "association",
                }
                for index in range(1, 10)
            ],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        },
        targeted_patch=None,
        generation_info={"source": "ai", "provider": "test", "model": "test-model"},
    )
    client = _build_client(
        CanvasService(repository=CanvasRepository(), ai_service=StubCanvasAiService(patch=ai_patch))
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-multirow-001/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [],
            "user_prompt": "生成一个十步流程图",
            "board_context": {},
            "session_metadata": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    nodes = response.json()["data"]["full_board"]["nodes"]
    position_by_id = {node["id"]: (node["x"], node["y"]) for node in nodes}
    assert position_by_id["step-1"] == (120, 140)
    assert position_by_id["step-4"] == (960, 140)
    assert position_by_id["step-5"] == (960, 320)
    assert position_by_id["step-6"] == (680, 320)
    assert position_by_id["step-8"] == (120, 320)
    assert position_by_id["step-9"] == (120, 500)
    assert position_by_id["step-10"] == (400, 500)


def test_generate_canvas_patch_prefers_ai_service_result_when_available() -> None:
    ai_patch = BoardPatchSchema(
        generation_mode="targeted_patch",
        patch_id="canvas-demo-ai-001-patch-llm",
        operations=[
            {
                "type": "node.replace",
                "target": "node-1",
                "content": "LLM 重写结果",
            }
        ],
        summary="由真实模型生成",
        full_board=None,
        generation_info={
            "source": "ai",
            "provider": "volcengine",
            "model": "ep-test-model",
        },
        targeted_patch={
            "selection": {"selectedNodeIds": ["node-1"]},
            "operations": [
                {
                    "type": "node.replace",
                    "target": "node-1",
                    "content": "LLM 重写结果",
                }
            ],
        },
    )
    client = _build_client(
        CanvasService(
            repository=CanvasRepository(),
            ai_service=StubCanvasAiService(patch=ai_patch),
        )
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-ai-001/generate",
        json={
            "generation_mode": "targeted_patch",
            "chat_context": [],
            "user_prompt": "请改写这个节点",
            "board_context": {"nodes": [{"id": "node-1", "text": "旧内容"}]},
            "session_metadata": {},
            "selection_context": {"selectedNodeIds": ["node-1"]},
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["patch_id"] == "canvas-demo-ai-001-patch-llm"
    assert payload["operations"][0]["content"] == "LLM 重写结果"
    assert payload["generation_info"]["source"] == "ai"
    assert payload["generation_info"]["provider"] == "volcengine"
    assert payload["generation_info"]["model"] == "ep-test-model"
    assert payload["generation_info"]["latency_ms"] >= 0


def test_generate_canvas_patch_returns_error_when_ai_service_fails() -> None:
    client = _build_client(
        CanvasService(
            repository=CanvasRepository(),
            ai_service=StubCanvasAiService(error=RuntimeError("llm unavailable")),
        )
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-ai-fallback-001/generate",
        json={
            "generation_mode": "targeted_patch",
            "chat_context": [],
            "user_prompt": "把选区拆成行动项",
            "board_context": {
                "nodes": [
                    {
                        "id": "node-1",
                        "text": "项目推进",
                        "x": 200,
                        "y": 180,
                        "width": 320,
                        "height": 96,
                    }
                ]
            },
            "session_metadata": {},
            "selection_context": {"selectedNodeIds": ["node-1"]},
        },
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["message"] == "Canvas AI generation failed"
    assert detail["reason"] == "llm unavailable"


def test_generate_canvas_patch_returns_error_when_ai_service_returns_empty_operations() -> None:
    empty_patch = BoardPatchSchema(
        generation_mode="targeted_patch",
        patch_id="canvas-demo-empty-ai-patch",
        operations=[],
        summary="empty",
        full_board=None,
        targeted_patch={"selection": {"selectedNodeIds": ["node-1"]}, "operations": []},
    )

    client = _build_client(
        CanvasService(
            repository=CanvasRepository(),
            ai_service=StubCanvasAiService(patch=empty_patch),
        )
    )

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-empty-ai/generate",
        json={
            "generation_mode": "targeted_patch",
            "chat_context": [],
            "user_prompt": "把选区拆成行动项",
            "board_context": {
                "nodes": [
                    {
                        "id": "node-1",
                        "text": "项目推进",
                        "x": 200,
                        "y": 180,
                        "width": 320,
                        "height": 96,
                    }
                ]
            },
            "session_metadata": {},
            "selection_context": {"selectedNodeIds": ["node-1"]},
        },
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["message"] == "Canvas AI generation failed"
    assert detail["reason"] == "AI returned an empty or incompatible canvas patch"


def test_http_canvas_ai_service_uses_volcengine_when_agent_key_is_empty() -> None:
    settings = type(
        "SettingsStub",
        (),
        {
            "AGENT_API_KEY": "",
            "AGENT_API_BASE": "https://api.deepseek.com",
            "AGENT_MODEL": "deepseek",
            "VOLCENGINE_API_KEY": "ark-test-key",
            "VOLCENGINE_ENDPOINT": "https://ark.cn-beijing.volces.com/api/v3",
            "VOLCENGINE_MODEL": "ep-test-model",
        },
    )()
    http_client = RecordingHttpClient()
    ai_service = HttpCanvasAiService(settings=settings, http_client=http_client)

    patch = ai_service.generate_patch(
        session_id="canvas-provider-test",
        payload=CanvasGenerationRequestSchema(
            generation_mode="targeted_patch",
            chat_context=[],
            user_prompt="改写节点",
            board_context={"nodes": [{"id": "node-1", "text": "旧内容"}]},
            session_metadata={},
            selection_context={"selectedNodeIds": ["node-1"]},
        ),
    )

    assert patch is not None
    assert patch.patch_id == "canvas-provider-test-patch"
    assert patch.generation_info["source"] == "ai"
    assert patch.generation_info["provider"] == "volcengine"
    assert patch.generation_info["model"] == "ep-test-model"
    assert http_client.calls[0]["url"] == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    assert http_client.calls[0]["headers"]["Authorization"] == "Bearer ark-test-key"
    assert http_client.calls[0]["json"]["model"] == "ep-test-model"
    assert http_client.calls[0]["json"]["max_tokens"] == 4096
    assert http_client.calls[0]["json"]["thinking"] == {"type": "disabled"}
    assert "response_format" not in http_client.calls[0]["json"]


def test_http_canvas_ai_service_retries_once_after_read_timeout() -> None:
    class TimeoutThenSuccessHttpClient(RecordingHttpClient):
        def post(self, url, headers, json):
            if not self.calls:
                self.calls.append({"url": url, "headers": headers, "json": json})
                raise httpx.ReadTimeout("model too slow")
            return super().post(url, headers, json)

    settings = type(
        "SettingsStub",
        (),
        {
            "AGENT_API_KEY": "",
            "AGENT_API_BASE": "https://api.deepseek.com",
            "AGENT_MODEL": "deepseek",
            "VOLCENGINE_API_KEY": "ark-test-key",
            "VOLCENGINE_ENDPOINT": "https://ark.cn-beijing.volces.com/api/v3",
            "VOLCENGINE_MODEL": "ep-test-model",
        },
    )()
    http_client = TimeoutThenSuccessHttpClient()
    ai_service = HttpCanvasAiService(settings=settings, http_client=http_client)

    patch = ai_service.generate_patch(
        session_id="canvas-provider-timeout-retry",
        payload=CanvasGenerationRequestSchema(
            generation_mode="targeted_patch",
            chat_context=[],
            user_prompt="改写节点",
            board_context={"nodes": [{"id": "node-1", "text": "旧内容"}]},
            session_metadata={},
            selection_context={"selectedNodeIds": ["node-1"]},
        ),
    )

    assert patch.operations[0]["content"] == "来自火山"
    assert len(http_client.calls) == 2
    assert http_client.calls[1]["json"]["max_tokens"] <= 2048
    retry_prompt = http_client.calls[1]["json"]["messages"][1]["content"]
    assert "retry_compact_canvas_patch" in retry_prompt


def test_http_canvas_ai_service_returns_local_fallback_after_repeated_read_timeout() -> None:
    class AlwaysTimeoutHttpClient:
        def __init__(self) -> None:
            self.calls = []

        def post(self, url, headers, json):
            self.calls.append({"url": url, "headers": headers, "json": json})
            raise httpx.ReadTimeout("model too slow")

    settings = type(
        "SettingsStub",
        (),
        {
            "AGENT_API_KEY": "",
            "AGENT_API_BASE": "https://api.deepseek.com",
            "AGENT_MODEL": "deepseek",
            "VOLCENGINE_API_KEY": "ark-test-key",
            "VOLCENGINE_ENDPOINT": "https://ark.cn-beijing.volces.com/api/v3",
            "VOLCENGINE_MODEL": "ep-test-model",
        },
    )()
    http_client = AlwaysTimeoutHttpClient()
    ai_service = HttpCanvasAiService(settings=settings, http_client=http_client)

    patch = ai_service.generate_patch(
        session_id="canvas-provider-timeout-fallback",
        payload=CanvasGenerationRequestSchema(
            generation_mode="full_board",
            chat_context=[],
            user_prompt="生成吃饭流程",
            board_context={},
            session_metadata={},
            selection_context=None,
        ),
    )

    assert len(http_client.calls) == 2
    assert patch.patch_id == "canvas-provider-timeout-fallback-timeout-fallback"
    assert patch.full_board is not None
    assert len(patch.full_board["nodes"]) >= 4
    assert patch.generation_info.provider == "volcengine-timeout-fallback"


def test_http_canvas_ai_service_retries_once_after_truncated_json() -> None:
    class TruncatedThenSuccessHttpClient(RecordingHttpClient):
        def post(self, url, headers, json):
            if not self.calls:
                self.calls.append({"url": url, "headers": headers, "json": json})

                class Response:
                    def raise_for_status(self_inner):
                        return None

                    def json(self_inner):
                        return {
                            "choices": [
                                {
                                    "message": {
                                        "content": '{"generation_mode":"targeted_patch","patch_id":"canvas-provider-test-patch","operations":[{"type":"node.replace","target":"node-1","content":'
                                    }
                                }
                            ]
                        }

                return Response()
            return super().post(url, headers, json)

    settings = type(
        "SettingsStub",
        (),
        {
            "AGENT_API_KEY": "",
            "AGENT_API_BASE": "https://api.deepseek.com",
            "AGENT_MODEL": "deepseek",
            "VOLCENGINE_API_KEY": "ark-test-key",
            "VOLCENGINE_ENDPOINT": "https://ark.cn-beijing.volces.com/api/v3",
            "VOLCENGINE_MODEL": "ep-test-model",
        },
    )()
    http_client = TruncatedThenSuccessHttpClient()
    ai_service = HttpCanvasAiService(settings=settings, http_client=http_client)

    patch = ai_service.generate_patch(
        session_id="canvas-provider-json-retry",
        payload=CanvasGenerationRequestSchema(
            generation_mode="targeted_patch",
            chat_context=[],
            user_prompt="改写节点",
            board_context={"nodes": [{"id": "node-1", "text": "旧内容"}]},
            session_metadata={},
            selection_context={"selectedNodeIds": ["node-1"]},
        ),
    )

    assert patch.operations[0]["content"] == "来自火山"
    assert len(http_client.calls) == 2
    retry_prompt = http_client.calls[1]["json"]["messages"][1]["content"]
    assert "retry_compact_canvas_patch" in retry_prompt


def test_http_canvas_ai_service_returns_local_fallback_after_repeated_truncated_json() -> None:
    class AlwaysTruncatedHttpClient:
        def __init__(self) -> None:
            self.calls = []

        def post(self, url, headers, json):
            self.calls.append({"url": url, "headers": headers, "json": json})

            class Response:
                def raise_for_status(self_inner):
                    return None

                def json(self_inner):
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": '{"generation_mode":"full_board","patch_id":"broken","full_board":{"nodes":[{"id":'
                                }
                            }
                        ]
                    }

            return Response()

    settings = type(
        "SettingsStub",
        (),
        {
            "AGENT_API_KEY": "",
            "AGENT_API_BASE": "https://api.deepseek.com",
            "AGENT_MODEL": "deepseek",
            "VOLCENGINE_API_KEY": "ark-test-key",
            "VOLCENGINE_ENDPOINT": "https://ark.cn-beijing.volces.com/api/v3",
            "VOLCENGINE_MODEL": "ep-test-model",
        },
    )()
    http_client = AlwaysTruncatedHttpClient()
    ai_service = HttpCanvasAiService(settings=settings, http_client=http_client)

    patch = ai_service.generate_patch(
        session_id="canvas-provider-json-fallback",
        payload=CanvasGenerationRequestSchema(
            generation_mode="full_board",
            chat_context=[],
            user_prompt="生成带 if else 的流程",
            board_context={},
            session_metadata={},
            selection_context=None,
        ),
    )

    assert len(http_client.calls) == 2
    assert patch.patch_id == "canvas-provider-json-fallback-invalid-json-fallback"
    assert patch.full_board is not None
    assert patch.summary == "模型输出 JSON 不完整，已生成本地降级流程图"
    assert patch.generation_info.provider == "volcengine-invalid-json-fallback"


def test_http_canvas_ai_service_prompt_allows_feishu_board_style_fields() -> None:
    payload = CanvasGenerationRequestSchema(
        generation_mode="full_board",
        chat_context=[],
        user_prompt="生成带样式的流程图",
        board_context={},
        session_metadata={},
        selection_context=None,
    )

    system_prompt = HttpCanvasAiService._build_system_prompt()
    prompt = json.loads(
        HttpCanvasAiService._build_prompt(
            session_id="canvas-style-prompt",
            payload=payload,
        )
    )

    assert "style, composite_shape, visual_role, shape_kind" in system_prompt
    assert "connector_style" in system_prompt
    assert "style_plan" in system_prompt
    assert len(system_prompt) < 1400
    assert prompt["feishu_board_style_contract"]["node_optional_fields"] == [
        "visual_role",
        "shape_kind",
        "style",
        "font_size",
        "font_weight",
        "theme_text_color_code",
        "theme_text_background_color_code",
    ]
    assert "flow_chart_diamond" in prompt["feishu_board_style_contract"]["shape_kind_values"]
    assert "border_width" in prompt["feishu_board_style_contract"]["style_fields"]
    assert prompt["style_plan_contract"]["field"] == "style_plan"
    assert prompt["style_plan_contract"]["available_templates"] == [
        "clean_flow",
        "sunset_flow",
        "forest_flow",
        "mono_exec",
    ]
    assert prompt["flow_structure_contract"]["decision_node"]["visual_role"] == "decision"
    assert "否" in prompt["flow_structure_contract"]["branch_edge_labels"]
    assert "返回" in prompt["flow_structure_contract"]["loop_edge_labels"]
    assert prompt["output_contract"]["style_plan"] == "optional style plan"
    assert prompt["feishu_board_style_contract"]["edge_optional_fields"] == [
        "label",
        "shape",
        "arrow_style",
        "start_arrow_style",
        "end_arrow_style",
        "style",
    ]
    prompt_text = json.dumps(prompt, ensure_ascii=False)
    assert len(prompt_text) < 4200
    assert "full_board_subway_flow" not in prompt["examples"]
    styled_node = prompt["examples"]["style_examples"]["nodes"][0]
    assert styled_node["visual_role"] == "start"
    assert styled_node["style"]["border_width"] == "medium"


def test_http_canvas_ai_service_prompt_compacts_runtime_context() -> None:
    verbose_nodes = [
        {
            "id": f"node-{index}",
            "type": "composite_shape",
            "text": f"步骤 {index}",
            "x": 120 + index * 260,
            "y": 160,
            "width": 240,
            "height": 100,
            "style": {
                "fill_color": "#e1eaff",
                "border_color": "#4e83fd",
                "border_width": "narrow",
                "raw_verbose_field": "x" * 200,
            },
            "raw_payload": {"ignored": "y" * 500},
        }
        for index in range(12)
    ]
    verbose_edges = [
        {
            "id": f"edge-{index}",
            "from": f"node-{index}",
            "to": f"node-{index + 1}",
            "type": "connector",
            "shape": "right_angled_polyline",
            "raw_payload": {"ignored": "z" * 300},
        }
        for index in range(11)
    ]
    payload = CanvasGenerationRequestSchema(
        generation_mode="full_board",
        chat_context=[
            {"role": "assistant", "content": f"历史回复 {index} " + "a" * 300}
            for index in range(8)
        ],
        user_prompt="生成后续吃完饭去健身房的步骤",
        board_context={
            "nodes": verbose_nodes,
            "edges": verbose_edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "raw_payload": {"ignored": "b" * 2000},
        },
        session_metadata={
            "source": {
                "source_type": "feishu_document_whiteboard",
                "document_token": "doc-token-001",
                "document_id": "doc-id-001",
                "whiteboard_id": "board-001",
                "block_id": "block-001",
                "raw_document": {"ignored": "c" * 2000},
                "raw_whiteboard": {"ignored": "d" * 2000},
            }
        },
        selection_context=None,
    )

    prompt_text = HttpCanvasAiService._build_prompt(
        session_id="canvas-compact-prompt",
        payload=payload,
    )
    prompt = json.loads(prompt_text)

    assert len(prompt_text) < 5600
    assert len(prompt["chat_context"]) == 4
    assert prompt["board_context"]["node_count"] == 12
    assert prompt["board_context"]["edge_count"] == 11
    assert "raw_payload" not in prompt["board_context"]
    assert "raw_payload" not in prompt["board_context"]["nodes"][0]
    assert "raw_verbose_field" not in json.dumps(prompt["board_context"], ensure_ascii=False)
    assert prompt["session_metadata"]["source"] == {
        "source_type": "feishu_document_whiteboard",
        "document_token": "doc-token-001",
        "document_id": "doc-id-001",
        "whiteboard_id": "board-001",
        "block_id": "block-001",
    }


def test_http_canvas_ai_service_rejects_patch_list_response() -> None:
    class PatchesHttpClient:
        def post(self, url, headers, json):
            class Response:
                def raise_for_status(self_inner):
                    return None

                def json(self_inner):
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": '{"patches":[{"op":"update","type":"node","id":"node-1","props":{"text":"整理后的总结"}}]}'
                                }
                            }
                        ]
                    }

            return Response()

    settings = type(
        "SettingsStub",
        (),
        {
            "AGENT_API_KEY": "",
            "AGENT_API_BASE": "https://api.deepseek.com",
            "AGENT_MODEL": "deepseek",
            "VOLCENGINE_API_KEY": "ark-test-key",
            "VOLCENGINE_ENDPOINT": "https://ark.cn-beijing.volces.com/api/v3",
            "VOLCENGINE_MODEL": "ep-test-model",
        },
    )()
    ai_service = HttpCanvasAiService(settings=settings, http_client=PatchesHttpClient())

    with pytest.raises(ValueError, match="missing generation_mode"):
        ai_service.generate_patch(
            session_id="canvas-provider-test",
            payload=CanvasGenerationRequestSchema(
                generation_mode="targeted_patch",
                chat_context=[],
                user_prompt="改写节点",
                board_context={"nodes": [{"id": "node-1", "text": "旧内容"}]},
                session_metadata={},
                selection_context={"selectedNodeIds": ["node-1"]},
            ),
        )


def test_http_canvas_ai_service_rejects_update_node_payload_response() -> None:
    class UpdateNodeHttpClient:
        def post(self, url, headers, json):
            class Response:
                def raise_for_status(self_inner):
                    return None

                def json(self_inner):
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": '{"patches":[{"type":"updateNode","payload":{"id":"node-1","text":"新的节点总结"}}]}'
                                }
                            }
                        ]
                    }

            return Response()

    settings = type(
        "SettingsStub",
        (),
        {
            "AGENT_API_KEY": "",
            "AGENT_API_BASE": "https://api.deepseek.com",
            "AGENT_MODEL": "deepseek",
            "VOLCENGINE_API_KEY": "ark-test-key",
            "VOLCENGINE_ENDPOINT": "https://ark.cn-beijing.volces.com/api/v3",
            "VOLCENGINE_MODEL": "ep-test-model",
        },
    )()
    ai_service = HttpCanvasAiService(settings=settings, http_client=UpdateNodeHttpClient())

    with pytest.raises(ValueError, match="missing generation_mode"):
        ai_service.generate_patch(
            session_id="canvas-provider-test",
            payload=CanvasGenerationRequestSchema(
                generation_mode="targeted_patch",
                chat_context=[],
                user_prompt="改写节点",
                board_context={"nodes": [{"id": "node-1", "text": "旧内容"}]},
                session_metadata={},
                selection_context={"selectedNodeIds": ["node-1"]},
            ),
        )


def test_create_merge_review_returns_pending_review() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-001/merge-review",
        json={
            "source_version": "v10",
            "working_version": 12,
            "conflicts": [{"element_id": "node-1", "kind": "text_conflict"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "pending_review"
    assert payload["review_id"] == "canvas-demo-001-merge-review-001"
    assert payload["source_version"] == "v10"
    assert payload["working_version"] == 12
    assert payload["events"][0]["event_type"] == "create"
    assert payload["events"][0]["source_version"] == "v10"
    assert payload["events"][0]["reason"] == "initial_review_created"
    assert payload["summary"] == {
        "total_conflicts": 1,
        "resolved_conflicts": 0,
        "pending_conflicts": 1,
    }
    assert payload["conflicts"] == [
        {
            "element_id": "node-1",
            "kind": "text_conflict",
            "source_version": "v10",
            "working_version": 12,
        }
    ]


def test_create_merge_review_includes_mapping_based_conflict_units(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-merge-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-merge-001",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-merge-001",
                title="Imported board",
                nodes=[
                    {"id": "node-1", "text": "Original"},
                    {"id": "node-2", "text": "Keep me"},
                ],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-demo-merge-001",
        BoardChangeSchema(
            change_id="change-merge-001",
            session_id="canvas-demo-merge-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-merge-001",
            target_scope="node:node-1",
            payload={
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {
                            "whiteboard_id": "source-board-merge-001",
                            "reason": "text divergence",
                        },
                    }
                ]
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-merge-001/merge-review",
        json={
            "source_version": "v10",
            "working_version": 2,
            "conflicts": [{"element_id": "node-1", "kind": "text_conflict"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "pending_review"
    assert payload["review_id"] == "canvas-demo-merge-001-merge-review-001"
    assert payload["source_version"] == "v10"
    assert payload["working_version"] == 2
    assert payload["summary"]["total_conflicts"] == 1
    assert payload["conflicts"][0]["element_id"] == "node-1"
    assert payload["conflicts"][0]["kind"] == "text_conflict"
    assert payload["conflicts"][0]["mapping_status"] == "conflicted"
    assert payload["conflicts"][0]["working_element_id"] == "node-1"
    assert payload["conflicts"][0]["source_element_id"] == "node-1"
    assert payload["conflicts"][0]["source_version"] == "v10"
    assert payload["conflicts"][0]["working_version"] == 2
    assert payload["conflicts"][0]["working_node"] == {"id": "node-1", "text": "Original"}
    assert payload["conflicts"][0]["source_node"] == {"id": "node-1", "text": "Original"}


def test_create_merge_review_derives_conflicts_from_conflicted_mappings(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-merge-002",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-merge-002",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-merge-002",
                title="Imported board",
                nodes=[
                    {"id": "node-1", "text": "Original"},
                    {"id": "node-2", "text": "Original 2"},
                ],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-demo-merge-002",
        BoardChangeSchema(
            change_id="change-merge-002",
            session_id="canvas-demo-merge-002",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-merge-002",
            target_scope="board:working",
            payload={
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {
                            "whiteboard_id": "source-board-merge-002",
                            "reason": "text divergence",
                            "kind": "text_conflict",
                        },
                    },
                    {
                        "source_element_id": "node-2",
                        "working_element_id": "node-2",
                        "element_type": "node",
                        "origin_type": "source_import",
                        "mapping_status": "active",
                        "metadata": {"whiteboard_id": "source-board-merge-002"},
                    },
                ]
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-merge-002/merge-review",
        json={
            "source_version": "v11",
            "working_version": 2,
            "conflicts": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "pending_review"
    assert payload["source_version"] == "v11"
    assert payload["working_version"] == 2
    assert payload["summary"]["pending_conflicts"] == 1
    assert len(payload["conflicts"]) == 1
    assert payload["conflicts"][0]["element_id"] == "node-1"
    assert payload["conflicts"][0]["kind"] == "text_conflict"
    assert payload["conflicts"][0]["mapping_status"] == "conflicted"
    assert payload["conflicts"][0]["working_element_id"] == "node-1"
    assert payload["conflicts"][0]["source_element_id"] == "node-1"
    assert payload["conflicts"][0]["origin_type"] == "merge"
    assert payload["conflicts"][0]["source_version"] == "v11"
    assert payload["conflicts"][0]["working_version"] == 2
    assert payload["conflicts"][0]["working_node"] == {"id": "node-1", "text": "Original"}
    assert payload["conflicts"][0]["source_node"] == {"id": "node-1", "text": "Original"}


def test_merge_resolve_with_source_choice_updates_working_node_and_clears_conflict(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-resolve-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-resolve-001",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-resolve-001",
                title="Imported board",
                nodes=[{"id": "node-1", "text": "Source text"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-demo-resolve-001",
        BoardChangeSchema(
            change_id="change-resolve-001",
            session_id="canvas-demo-resolve-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-resolve-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Working text"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Working text"}]},
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ],
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-resolve-001/merge-resolve",
        json={
            "review_id": "canvas-demo-resolve-001-merge-review-001",
            "actor_id": "reviewer-001",
            "resolutions": [
                {
                    "working_element_id": "node-1",
                    "resolution": "source",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "Source text"
    assert payload["element_mappings"][0]["mapping_status"] == "active"
    assert payload["element_mappings"][0]["metadata"]["resolved_by"] == "source"
    assert payload["session"]["sync_state"] == "idle"
    assert payload["recent_changes"][-1]["change_type"] == "merge_resolved"
    assert payload["recent_changes"][-1]["actor_id"] == "reviewer-001"

    review_response = client.get(
        "/api/v1/canvas/sessions/canvas-demo-resolve-001/merge-reviews/canvas-demo-resolve-001-merge-review-001"
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()["data"]
    assert review_payload["status"] == "resolved"
    assert review_payload["source_version"] == "feishu-normalized"
    assert review_payload["working_version"] == 3
    assert review_payload["events"][-1]["event_type"] == "resolve"
    assert review_payload["events"][-1]["actor_id"] == "reviewer-001"
    assert review_payload["events"][-1]["change_id"] == "canvas-demo-resolve-001-merge-resolved-3"
    assert review_payload["events"][-1]["resolutions"][0]["resolution"] == "source"
    assert review_payload["summary"] == {
        "total_conflicts": 1,
        "resolved_conflicts": 1,
        "pending_conflicts": 0,
    }
    assert review_payload["conflicts"][0]["resolution"] == "source"
    assert review_payload["conflicts"][0]["status"] == "resolved"


def test_merge_resolve_with_working_choice_keeps_working_node_and_clears_conflict(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-resolve-002",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-resolve-002",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-resolve-002",
                title="Imported board",
                nodes=[{"id": "node-1", "text": "Source text"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-demo-resolve-002",
        BoardChangeSchema(
            change_id="change-resolve-002",
            session_id="canvas-demo-resolve-002",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-resolve-002",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Working text"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Working text"}]},
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ],
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-resolve-002/merge-resolve",
        json={
            "review_id": "canvas-demo-resolve-002-merge-review-001",
            "actor_id": "reviewer-002",
            "resolutions": [
                {
                    "working_element_id": "node-1",
                    "resolution": "working",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "Working text"
    assert payload["element_mappings"][0]["mapping_status"] == "active"
    assert payload["element_mappings"][0]["metadata"]["resolved_by"] == "working"
    assert payload["session"]["sync_state"] == "idle"
    assert payload["recent_changes"][-1]["change_type"] == "merge_resolved"

    review_response = client.get(
        "/api/v1/canvas/sessions/canvas-demo-resolve-002/merge-reviews/canvas-demo-resolve-002-merge-review-001"
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()["data"]
    assert review_payload["status"] == "resolved"
    assert review_payload["source_version"] == "feishu-normalized"
    assert review_payload["working_version"] == 3
    assert review_payload["events"][-1]["event_type"] == "resolve"
    assert review_payload["events"][-1]["actor_id"] == "reviewer-002"
    assert review_payload["events"][-1]["change_id"] == "canvas-demo-resolve-002-merge-resolved-3"
    assert review_payload["conflicts"][0]["resolution"] == "working"


def test_merge_review_route_returns_persisted_review_after_creation(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-review-lookup-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-review-lookup-001",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-review-lookup-001",
                title="Imported board",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-demo-review-lookup-001",
        BoardChangeSchema(
            change_id="change-review-lookup-001",
            session_id="canvas-demo-review-lookup-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-review-lookup-001",
            target_scope="node:node-1",
            payload={
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ]
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    client = _build_client(canvas_service)

    create_response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-review-lookup-001/merge-review",
        json={
            "source_version": "v12",
            "working_version": 2,
            "conflicts": [],
        },
    )
    assert create_response.status_code == 200

    get_response = client.get(
        "/api/v1/canvas/sessions/canvas-demo-review-lookup-001/merge-reviews/canvas-demo-review-lookup-001-merge-review-001"
    )
    assert get_response.status_code == 200
    payload = get_response.json()["data"]
    assert payload["status"] == "pending_review"
    assert payload["source_version"] == "v12"
    assert payload["working_version"] == 2
    assert payload["events"][0]["event_type"] == "create"
    assert payload["events"][0]["reason"] == "initial_review_created"
    assert payload["summary"] == {
        "total_conflicts": 1,
        "resolved_conflicts": 0,
        "pending_conflicts": 1,
    }
    assert payload["conflicts"][0]["element_id"] == "node-1"


def test_create_merge_review_reuses_open_review_id_for_same_session(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-review-reuse-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-review-reuse-001",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-review-reuse-001",
                title="Imported board",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-demo-review-reuse-001",
        BoardChangeSchema(
            change_id="change-review-reuse-001",
            session_id="canvas-demo-review-reuse-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-review-reuse-001",
            target_scope="node:node-1",
            payload={
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ]
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    client = _build_client(canvas_service)

    first_response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-review-reuse-001/merge-review",
        json={
            "source_version": "v12",
            "working_version": 2,
            "conflicts": [],
        },
    )
    second_response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-review-reuse-001/merge-review",
        json={
            "source_version": "v12",
            "working_version": 2,
            "conflicts": [],
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["data"]["review_id"] == (
        "canvas-demo-review-reuse-001-merge-review-001"
    )
    assert second_response.json()["data"]["review_id"] == (
        "canvas-demo-review-reuse-001-merge-review-001"
    )


def test_create_merge_review_after_resolve_generates_next_review_id(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-review-seq-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-review-seq-001",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-review-seq-001",
                title="Imported board",
                nodes=[{"id": "node-1", "text": "Source text"}],
                edges=[],
            ),
        ),
    )
    canvas_service.apply_change(
        "canvas-demo-review-seq-001",
        BoardChangeSchema(
            change_id="change-review-seq-001",
            session_id="canvas-demo-review-seq-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-review-seq-001",
            target_scope="node:node-1",
            payload={
                "latest_snapshot": {"nodes": [{"id": "node-1", "text": "Working text"}]},
                "crdt_document": {"nodes": [{"id": "node-1", "text": "Working text"}]},
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ],
            },
            base_version="v1",
            result_version="v2",
        ),
    )
    client = _build_client(canvas_service)

    first_review = client.post(
        "/api/v1/canvas/sessions/canvas-demo-review-seq-001/merge-review",
        json={
            "source_version": "v12",
            "working_version": 2,
            "conflicts": [],
        },
    )
    assert first_review.status_code == 200
    assert first_review.json()["data"]["review_id"] == (
        "canvas-demo-review-seq-001-merge-review-001"
    )

    resolve_response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-review-seq-001/merge-resolve",
        json={
            "review_id": "canvas-demo-review-seq-001-merge-review-001",
            "actor_id": "reviewer-seq-001",
            "resolutions": [
                {
                    "working_element_id": "node-1",
                    "resolution": "source",
                }
            ],
        },
    )
    assert resolve_response.status_code == 200

    canvas_service.apply_change(
        "canvas-demo-review-seq-001",
        BoardChangeSchema(
            change_id="change-review-seq-002",
            session_id="canvas-demo-review-seq-001",
            change_type="user_edit",
            actor_type="user",
            actor_id="user-review-seq-002",
            target_scope="node:node-1",
            payload={
                "element_mappings": [
                    {
                        "source_element_id": "node-1",
                        "working_element_id": "node-1",
                        "element_type": "node",
                        "origin_type": "merge",
                        "mapping_status": "conflicted",
                        "metadata": {"kind": "text_conflict"},
                    }
                ]
            },
            base_version="v3",
            result_version="v4",
        ),
    )

    second_review = client.post(
        "/api/v1/canvas/sessions/canvas-demo-review-seq-001/merge-review",
        json={
            "source_version": "v13",
            "working_version": 4,
            "conflicts": [],
        },
    )

    assert second_review.status_code == 200
    assert second_review.json()["data"]["review_id"] == (
        "canvas-demo-review-seq-001-merge-review-002"
    )


def test_build_generation_request_from_feishu_document_adds_source_and_session_metadata() -> None:
    canvas_service = CanvasService(repository=CanvasRepository())
    document = FeishuDocumentContentSchema(
        document_token="doc-token-001",
        document_id="doc-id-001",
        title="飞书纪要",
        plain_text="项目背景\n核心目标",
        raw_content={"blocks": [{"block_id": "b1", "text": "项目背景"}]},
        share_url="https://example.feishu.cn/docx/doc-token-001",
    )

    generation_request = canvas_service.build_generation_request_from_feishu_document(
        document,
        user_prompt="整理成项目启动画板",
    )

    assert generation_request.board_context["source"]["source_type"] == "feishu_document"
    assert generation_request.board_context["source"]["document_token"] == "doc-token-001"
    assert generation_request.board_context["source"]["document_id"] == "doc-id-001"
    assert (
        generation_request.board_context["source"]["share_url"]
        == "https://example.feishu.cn/docx/doc-token-001"
    )
    assert generation_request.session_metadata == {
        "source": {
            "source_type": "feishu_document",
            "document_token": "doc-token-001",
            "document_id": "doc-id-001",
            "title": "飞书纪要",
            "share_url": "https://example.feishu.cn/docx/doc-token-001",
        },
        "session": {
            "mode": "document_to_canvas_generation",
            "conversation_id": "feishu-doc-doc-token-001",
            "title": "飞书纪要",
        },
    }


def test_apply_full_board_patch_updates_working_board_and_records_ai_change(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-apply-001",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-apply-001",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-001",
                title="Imported board",
                nodes=[{"id": "node-1", "text": "Imported"}],
                edges=[],
            ),
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-apply-001/apply-patch",
        json={
            "generation_mode": "full_board",
            "patch_id": "canvas-demo-apply-001-patch-001",
            "operations": [{"type": "board.create", "target": "canvas"}],
            "summary": "AI generated board",
            "full_board": {
                "nodes": [
                    {"id": "generated-node-1", "type": "topic", "text": "AI plan"}
                ],
                "edges": [],
                "viewport": {"x": 0, "y": 0, "zoom": 1},
            },
            "targeted_patch": None,
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["working_board"]["latest_version"] == 2
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "AI plan"
    assert payload["recent_changes"][-1]["change_type"] == "ai_patch"
    assert payload["recent_changes"][-1]["actor_type"] == "ai"
    assert payload["recent_changes"][-1]["actor_id"] == "patch:canvas-demo-apply-001-patch-001"
    assert payload["recent_changes"][-1]["target_scope"] == "board:working"


def test_apply_full_board_patch_applies_clean_flow_style_template(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-style-template",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-style-template",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-style-template",
                title="Imported board",
                nodes=[],
                edges=[],
            ),
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-style-template/apply-patch",
        json={
            "generation_mode": "full_board",
            "patch_id": "canvas-demo-style-template-patch-001",
            "operations": [],
            "summary": "AI generated styled board",
            "full_board": {
                "nodes": [
                    {"id": "start", "type": "topic", "text": "开始"},
                    {
                        "id": "decision",
                        "type": "note",
                        "text": "是否准备好?",
                        "shape_kind": "flow_chart_diamond",
                    },
                    {"id": "end", "type": "topic", "text": "结束"},
                ],
                "edges": [
                    {"id": "edge-1", "from": "start", "to": "decision", "label": "下一步"},
                    {"id": "edge-2", "from": "decision", "to": "end", "label": "是"},
                ],
                "viewport": {"x": 0, "y": 0, "zoom": 1},
            },
            "targeted_patch": None,
        },
    )

    assert response.status_code == 200
    snapshot = response.json()["data"]["working_board"]["latest_snapshot"]
    nodes = {node["id"]: node for node in snapshot["nodes"]}
    edges = {edge["id"]: edge for edge in snapshot["edges"]}
    assert nodes["start"]["visual_role"] == "start"
    assert nodes["start"]["style"]["fill_color"] == "#e7f8ef"
    assert nodes["decision"]["style"]["border_color"] == "#f59e0b"
    assert nodes["decision"]["font_weight"] == "bold"
    assert nodes["end"]["visual_role"] == "end"
    assert edges["edge-1"]["shape"] == "right_angled_polyline"
    assert edges["edge-1"]["arrow_style"] == "triangle_arrow"
    assert edges["edge-2"]["style"]["border_color"] == "#9ca3af"


def test_apply_targeted_patch_updates_matching_node_and_keeps_other_nodes(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-apply-002",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-apply-002",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-002",
                title="Imported board",
                nodes=[
                    {"id": "node-1", "text": "Original"},
                    {"id": "node-2", "text": "Keep me"},
                ],
                edges=[],
            ),
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-apply-002/apply-patch",
        json={
            "generation_mode": "targeted_patch",
            "patch_id": "canvas-demo-apply-002-patch-001",
            "operations": [
                {
                    "type": "node.replace",
                    "target": "node-1",
                    "content": "Updated by AI",
                },
                {
                    "type": "node.add",
                    "target": "canvas",
                    "node": {
                        "id": "canvas-demo-apply-002-node-1-step-1",
                        "type": "note",
                        "text": "阶段 1：现状盘点",
                        "x": 420,
                        "y": 40,
                        "width": 220,
                        "height": 100,
                    },
                },
                {
                    "type": "edge.add",
                    "target": "canvas",
                    "edge": {
                        "id": "canvas-demo-apply-002-node-1-step-edge-1",
                        "from": "node-1",
                        "to": "canvas-demo-apply-002-node-1-step-1",
                        "type": "association",
                    },
                },
            ],
            "summary": "AI updated one node",
            "full_board": None,
            "targeted_patch": {
                "selection": {"selectedNodeIds": ["node-1"]},
                "operations": [
                    {
                        "type": "node.replace",
                        "target": "node-1",
                        "content": "Updated by AI",
                    },
                    {
                        "type": "node.add",
                        "target": "canvas",
                        "node": {
                            "id": "canvas-demo-apply-002-node-1-step-1",
                            "type": "note",
                            "text": "阶段 1：现状盘点",
                            "x": 420,
                            "y": 40,
                            "width": 220,
                            "height": 100,
                        },
                    },
                    {
                        "type": "edge.add",
                        "target": "canvas",
                        "edge": {
                            "id": "canvas-demo-apply-002-node-1-step-edge-1",
                            "from": "node-1",
                            "to": "canvas-demo-apply-002-node-1-step-1",
                            "type": "association",
                        },
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["working_board"]["latest_version"] == 2
    nodes = payload["working_board"]["latest_snapshot"]["nodes"]
    assert [node["id"] for node in nodes] == [
        "node-1",
        "node-2",
        "canvas-demo-apply-002-node-1-step-1",
    ]
    assert nodes[0]["text"] == "Updated by AI"
    assert nodes[1]["text"] == "Keep me"
    assert nodes[2]["text"] == "阶段 1：现状盘点"
    assert nodes[2]["x"] == 420
    assert nodes[2]["style"]["border_color"] == "#2563eb"
    edges = payload["working_board"]["latest_snapshot"]["edges"]
    assert edges[0]["id"] == "canvas-demo-apply-002-node-1-step-edge-1"
    assert edges[0]["from"] == "node-1"
    assert edges[0]["to"] == "canvas-demo-apply-002-node-1-step-1"
    assert edges[0]["shape"] == "right_angled_polyline"
    assert payload["recent_changes"][-1]["change_type"] == "ai_patch"
    assert payload["recent_changes"][-1]["target_scope"] == "node:node-1"


def test_apply_targeted_patch_stringifies_structured_replace_content(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-apply-structured-replace",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-apply-structured-replace",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-structured-replace",
                title="Imported board",
                nodes=[{"id": "node-1", "text": "Original"}],
                edges=[],
            ),
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-apply-structured-replace/apply-patch",
        json={
            "generation_mode": "targeted_patch",
            "patch_id": "structured-replace-patch-001",
            "operations": [
                {
                    "type": "node.replace",
                    "target": "node-1",
                    "content": {"text": "Updated by AI", "style": {"fill_color": "#e1eaff"}},
                }
            ],
            "summary": "AI updated one node",
            "full_board": None,
            "targeted_patch": {
                "selection": {"selectedNodeIds": ["node-1"]},
                "operations": [
                    {
                        "type": "node.replace",
                        "target": "node-1",
                        "content": {
                            "text": "Updated by AI",
                            "style": {"fill_color": "#e1eaff"},
                        },
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["working_board"]["latest_snapshot"]["nodes"][0]["text"] == "Updated by AI"


def test_apply_targeted_patch_can_add_new_node_and_mapping(tmp_path) -> None:
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))
    canvas_service.ingest_feishu_board(
        "canvas-demo-apply-004",
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-demo-apply-004",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-004",
                title="Imported board",
                nodes=[
                    {"id": "node-1", "text": "Original", "x": 120, "y": 80},
                ],
                edges=[],
            ),
        ),
    )
    client = _build_client(canvas_service)

    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-apply-004/apply-patch",
        json={
            "generation_mode": "targeted_patch",
            "patch_id": "canvas-demo-apply-004-patch-001",
            "operations": [
                {
                    "type": "node.add",
                    "target": "canvas",
                    "node": {
                        "id": "canvas-demo-apply-004-generated-node-1",
                        "type": "note",
                        "text": "新增行动项",
                        "x": 480,
                        "y": 120,
                        "width": 240,
                        "height": 120,
                    },
                }
            ],
            "summary": "AI added one node",
            "full_board": None,
            "targeted_patch": {
                "selection": {},
                "operations": [
                    {
                        "type": "node.add",
                        "target": "canvas",
                        "node": {
                            "id": "canvas-demo-apply-004-generated-node-1",
                            "type": "note",
                            "text": "新增行动项",
                            "x": 480,
                            "y": 120,
                            "width": 240,
                            "height": 120,
                        },
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["working_board"]["latest_version"] == 2
    generated_node = payload["working_board"]["latest_snapshot"]["nodes"][1]
    assert generated_node["id"] == "canvas-demo-apply-004-generated-node-1"
    assert generated_node["type"] == "note"
    assert generated_node["text"] == "新增行动项"
    assert generated_node["x"] == 480
    assert generated_node["y"] == 120
    assert generated_node["width"] == 240
    assert generated_node["height"] == 120
    assert generated_node["shape_kind"] == "flow_chart_round_rect"
    assert payload["recent_changes"][-1]["target_scope"] == "board:working"
    assert payload["element_mappings"][-1]["origin_type"] == "ai"
    assert payload["element_mappings"][-1]["working_element_id"] == (
        "canvas-demo-apply-004-generated-node-1"
    )
