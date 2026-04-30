# Feishu Board Task Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a backend-first Feishu board generation pipeline that accepts `message + sharing_url`, turns the request into a validated `BoardPlan` via LLM prompting, writes nodes to a Feishu whiteboard, and exposes task status for a thin web UI.

**Architecture:** Keep the pipeline aligned with `/Users/klot/Downloads/feishu_board_renderer_plan.md`: the LLM produces `BoardPlan` JSON only, while Python performs validation, layout, styling, serialization, and Feishu API orchestration. Land the MVP under the existing `canvas` module so routing stays stable, then add a minimal HTML surface for status viewing because the repo currently lacks editable frontend source files.

**Tech Stack:** FastAPI, Pydantic, pytest, httpx/requests-compatible Feishu client wiring, server-rendered HTML or static response for the thin UI.

---

### Task 1: Lock the board task API contract

**Files:**
- Create: `backend/tests/modules/test_canvas_board_task_contract.py`
- Modify: `backend/tests/modules/test_module_registration.py`
- Modify: `backend/app/modules/canvas/schemas.py`
- Modify: `backend/app/modules/canvas/router.py`

- [ ] **Step 1: Write the failing task creation and task fetch contract tests**

```python
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container


def _build_client() -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    return TestClient(app)


def test_create_board_task_returns_pending_task() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/canvas/board/tasks",
        json={
            "message": "生成一个 AI 研发流程图",
            "sharing_url": "https://example.feishu.cn/docx/demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "pending"
    assert payload["data"]["message"] == "生成一个 AI 研发流程图"
    assert payload["data"]["sharing_url"] == "https://example.feishu.cn/docx/demo"
    assert payload["data"]["current_step"] == "pending"
    assert payload["data"]["logs"] == []


def test_get_board_task_returns_latest_task_state() -> None:
    client = _build_client()

    create_response = client.post(
        "/api/v1/canvas/board/tasks",
        json={
            "message": "生成一个 AI 研发流程图",
            "sharing_url": "https://example.feishu.cn/docx/demo",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    response = client.get(f"/api/v1/canvas/board/tasks/{task_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["task_id"] == task_id
    assert payload["data"]["status"] == "pending"
```

- [ ] **Step 2: Run the new tests to verify they fail for the missing routes**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_canvas_board_task_contract.py -v`
Expected: FAIL with `404` responses or import errors because the board task routes and schemas do not exist yet.

- [ ] **Step 3: Add request/response schemas and routes with stub behavior**

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CanvasBoardTaskCreateRequest(BaseModel):
    message: str
    sharing_url: str
    title: str | None = None
    replace_existing: bool = False


class CanvasBoardTaskLogSchema(BaseModel):
    step: str
    message: str


class CanvasBoardTaskSchema(BaseModel):
    task_id: str
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"
    current_step: Literal[
        "pending",
        "resolving_target",
        "planning",
        "rendering",
        "exporting_preview",
        "succeeded",
        "failed",
    ] = "pending"
    message: str
    sharing_url: str
    title: str | None = None
    whiteboard_id: str | None = None
    preview_url: str | None = None
    error_message: str | None = None
    result_summary: str | None = None
    logs: list[CanvasBoardTaskLogSchema] = Field(default_factory=list)
```

```python
@router.post(
    "/board/tasks",
    response_model=ApiResponse[CanvasBoardTaskSchema],
    summary="创建飞书画板生成任务",
)
async def create_board_task(
    payload: CanvasBoardTaskCreateRequest,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasBoardTaskSchema]:
    return ApiResponse.success(canvas_service.create_board_task(payload))


@router.get(
    "/board/tasks/{task_id}",
    response_model=ApiResponse[CanvasBoardTaskSchema],
    summary="获取飞书画板生成任务",
)
async def get_board_task(
    task_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[CanvasBoardTaskSchema]:
    return ApiResponse.success(canvas_service.get_board_task(task_id))
```

- [ ] **Step 4: Run the contract tests to verify the stub contract passes**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_canvas_board_task_contract.py tests/modules/test_module_registration.py -v`
Expected: PASS for the new board task routes and updated router registry expectations.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/modules/test_canvas_board_task_contract.py \
  backend/tests/modules/test_module_registration.py \
  backend/app/modules/canvas/schemas.py \
  backend/app/modules/canvas/router.py
git commit -m "feat: add board task API contract"
```

### Task 2: Add in-memory task storage and service orchestration skeleton

**Files:**
- Modify: `backend/app/modules/canvas/repository.py`
- Modify: `backend/app/modules/canvas/service.py`
- Create: `backend/tests/modules/test_canvas_board_task_service.py`

- [ ] **Step 1: Write the failing service behavior tests**

```python
from __future__ import annotations

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import CanvasBoardTaskCreateRequest
from app.modules.canvas.service import CanvasService


def test_create_board_task_persists_new_task() -> None:
    service = CanvasService(repository=CanvasRepository())

    task = service.create_board_task(
        CanvasBoardTaskCreateRequest(
            message="生成一个 AI 研发流程图",
            sharing_url="https://example.feishu.cn/docx/demo",
        )
    )

    loaded = service.get_board_task(task.task_id)

    assert loaded.task_id == task.task_id
    assert loaded.message == "生成一个 AI 研发流程图"
    assert loaded.current_step == "pending"


def test_run_board_task_marks_progress_and_completion() -> None:
    service = CanvasService(repository=CanvasRepository())
    task = service.create_board_task(
        CanvasBoardTaskCreateRequest(
            message="生成一个 AI 研发流程图",
            sharing_url="https://example.feishu.cn/docx/demo",
        )
    )

    completed = service.run_board_task(task.task_id)

    assert completed.status == "succeeded"
    assert completed.current_step == "succeeded"
    assert completed.logs[-1].step == "succeeded"
```

- [ ] **Step 2: Run the tests to verify they fail because the repository and service do not support board tasks**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_canvas_board_task_service.py -v`
Expected: FAIL with missing methods or wrong constructor errors.

- [ ] **Step 3: Implement an in-memory board task store and service methods**

```python
from __future__ import annotations

from uuid import uuid4

from app.modules.canvas.schemas import (
    CanvasBoardTaskCreateRequest,
    CanvasBoardTaskLogSchema,
    CanvasBoardTaskSchema,
)


class CanvasRepository:
    def __init__(self) -> None:
        self._board_tasks: dict[str, CanvasBoardTaskSchema] = {}

    def create_board_task(self, payload: CanvasBoardTaskCreateRequest) -> CanvasBoardTaskSchema:
        task = CanvasBoardTaskSchema(
            task_id=f"board-task-{uuid4().hex[:12]}",
            message=payload.message,
            sharing_url=payload.sharing_url,
            title=payload.title,
        )
        self._board_tasks[task.task_id] = task
        return task

    def get_board_task(self, task_id: str) -> CanvasBoardTaskSchema:
        return self._board_tasks[task_id]

    def save_board_task(self, task: CanvasBoardTaskSchema) -> CanvasBoardTaskSchema:
        self._board_tasks[task.task_id] = task
        return task
```

```python
def run_board_task(self, task_id: str) -> CanvasBoardTaskSchema:
    task = self._repository.get_board_task(task_id)
    running = task.model_copy(
        update={
            "status": "running",
            "current_step": "resolving_target",
            "logs": [*task.logs, CanvasBoardTaskLogSchema(step="resolving_target", message="开始解析分享链接")],
        }
    )
    self._repository.save_board_task(running)
    completed = running.model_copy(
        update={
            "status": "succeeded",
            "current_step": "succeeded",
            "result_summary": "stub pipeline completed",
            "logs": [*running.logs, CanvasBoardTaskLogSchema(step="succeeded", message="任务执行完成")],
        }
    )
    return self._repository.save_board_task(completed)
```

- [ ] **Step 4: Run the tests to verify the service skeleton passes**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_canvas_board_task_service.py tests/modules/test_canvas_board_task_contract.py -v`
Expected: PASS with persisted tasks and deterministic stub execution.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/canvas/repository.py \
  backend/app/modules/canvas/service.py \
  backend/tests/modules/test_canvas_board_task_service.py
git commit -m "feat: add board task service skeleton"
```

### Task 3: Implement board plan models, prompt builder, and validation

**Files:**
- Create: `backend/app/board_renderer/__init__.py`
- Create: `backend/app/board_renderer/models.py`
- Create: `backend/app/board_renderer/prompt.py`
- Create: `backend/app/board_renderer/validator.py`
- Create: `backend/tests/modules/test_board_renderer_models.py`

- [ ] **Step 1: Write the failing tests for BoardPlan parsing and validation**

```python
from __future__ import annotations

import pytest

from app.board_renderer.models import BoardPlan
from app.board_renderer.prompt import build_board_plan_messages
from app.board_renderer.validator import validate_board_plan_edges


def test_build_board_plan_messages_mentions_json_only_contract() -> None:
    messages = build_board_plan_messages("生成一个 AI 研发流程图")

    assert "BoardPlan JSON" in messages["system"]
    assert "Do not output Feishu OpenAPI JSON" in messages["system"]
    assert messages["user"] == "生成一个 AI 研发流程图"


def test_validate_board_plan_edges_rejects_unknown_nodes() -> None:
    plan = BoardPlan.model_validate(
        {
            "title": "AI 研发流程图",
            "diagram_type": "layered_architecture",
            "groups": [
                {
                    "id": "inputs",
                    "title": "Inputs",
                    "role": "input",
                    "nodes": [{"id": "user_request", "title": "User Request", "kind": "task"}],
                }
            ],
            "edges": [{"source": "user_request", "target": "missing_node", "kind": "main"}],
        }
    )

    with pytest.raises(ValueError, match="missing_node"):
        validate_board_plan_edges(plan)
```

- [ ] **Step 2: Run the tests to verify they fail because the board renderer package is missing**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_board_renderer_models.py -v`
Expected: FAIL with `ModuleNotFoundError` for `app.board_renderer`.

- [ ] **Step 3: Implement the BoardPlan models, prompt builder, and edge validator**

```python
DiagramType = Literal[
    "layered_architecture",
    "flowchart",
    "matrix",
    "timeline",
    "kanban",
    "org_chart",
    "island_topology",
]


class BoardPlan(BaseModel):
    title: str
    diagram_type: DiagramType
    layout: BoardLayoutPlan = Field(default_factory=BoardLayoutPlan)
    groups: list[BoardGroupPlan]
    edges: list[BoardEdgePlan] = Field(default_factory=list)
    palette: Literal["classic", "business", "tech", "fresh", "minimal"] = "classic"
```

```python
def build_board_plan_messages(user_message: str) -> dict[str, str]:
    system = "\n".join(
        [
            "You are a Feishu board information-architecture planner.",
            "Convert the user request into BoardPlan JSON.",
            "Do not output Feishu OpenAPI JSON.",
            "Do not output x, y, width, height, style, z_index, connector.",
            "Only output valid JSON. No Markdown. No explanation.",
        ]
    )
    return {"system": system, "user": user_message}
```

```python
def validate_board_plan_edges(plan: BoardPlan) -> BoardPlan:
    node_ids = {
        node.id
        for group in plan.groups
        for node in group.nodes
    }
    for edge in plan.edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            raise ValueError(
                f"Board edge references unknown node: {edge.source}->{edge.target}"
            )
    return plan
```

- [ ] **Step 4: Run the tests to verify board plan parsing and validation pass**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_board_renderer_models.py -v`
Expected: PASS with prompt rules and validation behavior covered.

- [ ] **Step 5: Commit**

```bash
git add backend/app/board_renderer backend/tests/modules/test_board_renderer_models.py
git commit -m "feat: add board plan models and validation"
```

### Task 4: Add sharing URL resolution and Feishu board client stubs

**Files:**
- Create: `backend/app/modules/feishu/board_client.py`
- Create: `backend/app/modules/feishu/board_target.py`
- Create: `backend/tests/modules/test_feishu_board_target.py`
- Modify: `backend/app/modules/feishu/__init__.py`

- [ ] **Step 1: Write the failing tests for sharing URL parsing**

```python
from __future__ import annotations

from app.modules.feishu.board_target import resolve_board_target_from_sharing_url


def test_resolve_board_target_accepts_whiteboard_like_url() -> None:
    target = resolve_board_target_from_sharing_url(
        "https://example.feishu.cn/board/wbcnAABBCC"
    )

    assert target.whiteboard_id == "wbcnAABBCC"
    assert target.source_kind == "whiteboard"


def test_resolve_board_target_falls_back_to_document_target() -> None:
    target = resolve_board_target_from_sharing_url(
        "https://example.feishu.cn/docx/AbCdEfGhIjKl"
    )

    assert target.doc_token == "AbCdEfGhIjKl"
    assert target.source_kind == "document"
```

- [ ] **Step 2: Run the tests to verify they fail because the parser module is missing**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_feishu_board_target.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the target parser and a Feishu board client stub**

```python
class BoardTarget(BaseModel):
    source_kind: Literal["whiteboard", "document"]
    whiteboard_id: str | None = None
    doc_token: str | None = None


def resolve_board_target_from_sharing_url(sharing_url: str) -> BoardTarget:
    parsed = urlparse(sharing_url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    if "board" in segments and segments[-1]:
        return BoardTarget(source_kind="whiteboard", whiteboard_id=segments[-1])
    if "docx" in segments and segments[-1]:
        return BoardTarget(source_kind="document", doc_token=segments[-1])
    raise ValueError(f"Unsupported Feishu sharing url: {sharing_url}")
```

```python
class FeishuBoardClient:
    def list_nodes(self, whiteboard_id: str) -> list[dict[str, object]]:
        return []

    def create_nodes(self, whiteboard_id: str, nodes: list[dict[str, object]]) -> dict[str, object]:
        return {"whiteboard_id": whiteboard_id, "count": len(nodes)}

    def batch_delete_nodes(self, whiteboard_id: str, node_ids: list[str]) -> dict[str, object]:
        return {"whiteboard_id": whiteboard_id, "deleted": len(node_ids)}

    def download_as_image(self, whiteboard_id: str) -> str:
        return f"https://stub.preview/{whiteboard_id}.png"
```

- [ ] **Step 4: Run the tests to verify sharing URL resolution passes**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_feishu_board_target.py -v`
Expected: PASS with both whiteboard and document link parsing covered.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/feishu/board_client.py \
  backend/app/modules/feishu/board_target.py \
  backend/tests/modules/test_feishu_board_target.py
git commit -m "feat: add feishu board target parsing"
```

### Task 5: Wire the board generation service end-to-end with deterministic stubs

**Files:**
- Create: `backend/app/services/board_generate_service.py`
- Create: `backend/tests/modules/test_board_generate_service.py`
- Modify: `backend/app/modules/canvas/dependencies.py`
- Modify: `backend/app/modules/canvas/service.py`

- [ ] **Step 1: Write the failing orchestration tests**

```python
from __future__ import annotations

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import CanvasBoardTaskCreateRequest
from app.modules.canvas.service import CanvasService
from app.modules.feishu.board_client import FeishuBoardClient
from app.services.board_generate_service import BoardGenerateService


def test_board_generate_service_runs_task_to_preview() -> None:
    generator = BoardGenerateService(feishu_board_client=FeishuBoardClient())

    result = generator.generate(
        message="生成一个 AI 研发流程图",
        sharing_url="https://example.feishu.cn/board/wbcnAABBCC",
    )

    assert result.whiteboard_id == "wbcnAABBCC"
    assert result.preview_url == "https://stub.preview/wbcnAABBCC.png"
    assert "创建了" in result.result_summary


def test_canvas_service_run_board_task_uses_generator_result() -> None:
    repository = CanvasRepository()
    generator = BoardGenerateService(feishu_board_client=FeishuBoardClient())
    service = CanvasService(repository=repository, board_generate_service=generator)
    task = service.create_board_task(
        CanvasBoardTaskCreateRequest(
            message="生成一个 AI 研发流程图",
            sharing_url="https://example.feishu.cn/board/wbcnAABBCC",
        )
    )

    completed = service.run_board_task(task.task_id)

    assert completed.status == "succeeded"
    assert completed.whiteboard_id == "wbcnAABBCC"
    assert completed.preview_url == "https://stub.preview/wbcnAABBCC.png"
```

- [ ] **Step 2: Run the tests to verify they fail because the generator service is missing**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_board_generate_service.py -v`
Expected: FAIL with missing imports or constructor mismatch.

- [ ] **Step 3: Implement the generator service and wire it into CanvasService**

```python
class BoardGenerateResult(BaseModel):
    whiteboard_id: str
    preview_url: str
    result_summary: str


class BoardGenerateService:
    def __init__(self, feishu_board_client: FeishuBoardClient) -> None:
        self._feishu_board_client = feishu_board_client

    def generate(self, *, message: str, sharing_url: str) -> BoardGenerateResult:
        target = resolve_board_target_from_sharing_url(sharing_url)
        whiteboard_id = target.whiteboard_id or f"resolved-from-{target.doc_token}"
        nodes = [
            {"type": "section", "title": "需求分析"},
            {"type": "composite_shape", "title": message[:20]},
        ]
        create_result = self._feishu_board_client.create_nodes(whiteboard_id, nodes)
        preview_url = self._feishu_board_client.download_as_image(whiteboard_id)
        return BoardGenerateResult(
            whiteboard_id=whiteboard_id,
            preview_url=preview_url,
            result_summary=f"创建了 {create_result['count']} 个节点",
        )
```

- [ ] **Step 4: Run the orchestration tests to verify the end-to-end stub pipeline passes**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_board_generate_service.py tests/modules/test_canvas_board_task_service.py -v`
Expected: PASS with a deterministic backend-only pipeline from task to preview URL.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/board_generate_service.py \
  backend/app/modules/canvas/dependencies.py \
  backend/app/modules/canvas/service.py \
  backend/tests/modules/test_board_generate_service.py
git commit -m "feat: wire board generation task pipeline"
```

### Task 6: Add a thin web-facing status page for manual testing

**Files:**
- Create: `backend/app/modules/canvas/ui_router.py`
- Create: `backend/tests/modules/test_canvas_board_ui.py`
- Modify: `backend/app/core/container.py`

- [ ] **Step 1: Write the failing UI smoke test**

```python
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container


def test_board_ui_page_renders_form_labels() -> None:
    app = FastAPI()
    container.register_routers(app)
    client = TestClient(app)

    response = client.get("/canvas/board")

    assert response.status_code == 200
    assert "Feishu Board Generator" in response.text
    assert "sharing_url" in response.text
    assert "message" in response.text
```

- [ ] **Step 2: Run the test to verify it fails because the UI route is missing**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_canvas_board_ui.py -v`
Expected: FAIL with `404`.

- [ ] **Step 3: Implement a minimal HTML page under FastAPI**

```python
router = APIRouter()


@router.get("/canvas/board", response_class=HTMLResponse, summary="画板生成测试页")
async def board_ui() -> HTMLResponse:
    return HTMLResponse(
        """
        <html>
          <head><title>Feishu Board Generator</title></head>
          <body>
            <h1>Feishu Board Generator</h1>
            <form>
              <label for="sharing_url">sharing_url</label>
              <input id="sharing_url" name="sharing_url" />
              <label for="message">message</label>
              <textarea id="message" name="message"></textarea>
            </form>
          </body>
        </html>
        """
    )
```

- [ ] **Step 4: Run the UI smoke test to verify the page renders**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_canvas_board_ui.py tests/modules/test_module_registration.py -v`
Expected: PASS with `/canvas/board` served alongside the API routes.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/canvas/ui_router.py \
  backend/app/core/container.py \
  backend/tests/modules/test_canvas_board_ui.py
git commit -m "feat: add thin board testing page"
```

### Task 7: Verification sweep and contract clean-up

**Files:**
- Modify: `backend/tests/modules/test_module_registration.py`
- Modify: `backend/tests/test_app_routes.py`
- Modify: any files touched above if verification exposes gaps

- [ ] **Step 1: Write any missing failing assertions for route registration and startup safety**

```python
expected_surface = {
    "/api/v1/canvas/board/tasks": {"POST"},
    "/api/v1/canvas/board/tasks/{task_id}": {"GET"},
    "/canvas/board": {"GET"},
}
```

- [ ] **Step 2: Run the full focused backend suite to verify the new expectations fail before clean-up**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_module_registration.py tests/test_app_routes.py -v`
Expected: FAIL if any new routes are not fully reflected in the registration expectations.

- [ ] **Step 3: Update the remaining assertions and fix any regressions**

```python
assert payload["data"]["status"] == "pending"
assert payload["data"]["current_step"] == "pending"
```

- [ ] **Step 4: Run the final focused verification suite**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_canvas_board_task_contract.py tests/modules/test_canvas_board_task_service.py tests/modules/test_board_renderer_models.py tests/modules/test_feishu_board_target.py tests/modules/test_board_generate_service.py tests/modules/test_canvas_board_ui.py tests/modules/test_module_registration.py tests/test_app_routes.py -v`
Expected: PASS across the new board pipeline contract, orchestration, and UI smoke tests.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/modules/test_module_registration.py \
  backend/tests/test_app_routes.py
git commit -m "test: verify board pipeline contracts"
```
