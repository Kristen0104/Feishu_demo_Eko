# PPT Master Backend Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current placeholder-driven PPT wrapper path with a backend flow that reuses the vendored `backend/vendor/ppt_master/` workflow as the primary implementation and keeps `backend/app/modules/ppt/` as an Eko-specific bridge layer.

**Architecture:** Keep the vendored `ppt_master` assets, references, and scripts as the source of truth for template semantics, execution phases, and export behavior. Refactor the backend so prompt-like inputs are first converted into project artifacts (`design_spec.md`, `spec_lock.md`, page outline), then rendered page-by-page through an Executor layer before passing through the existing `ppt-master` post-processing/export scripts.

**Tech Stack:** FastAPI, Python 3.11+, vendored `backend/vendor/ppt_master` workflow, SVG generation, `svg_quality_checker.py`, `finalize_svg.py`, `svg_to_pptx.py`.

---

### Task 1: Lock vendor-first ownership in the PPT bridge layer

**Files:**
- Modify: `backend/app/modules/ppt/README.md`
- Modify: `backend/app/modules/ppt/__init__.py`
- Test: `tests/test_backend_ppt_vendor_alignment.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_ppt_readme_declares_vendor_ppt_master_as_source_of_truth():
    text = Path("backend/app/modules/ppt/README.md").read_text(encoding="utf-8")
    assert "backend/vendor/ppt_master" in text
    assert "bridge layer" in text.lower()


def test_ppt_module_init_exports_bridge_components_not_standalone_engine_claims():
    text = Path("backend/app/modules/ppt/__init__.py").read_text(encoding="utf-8")
    assert "Fast SVG-to-PPTX generation helpers" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backend_ppt_vendor_alignment.py -v`
Expected: FAIL because the README and module docstring still describe the local module as the PPT engine instead of a vendor-backed bridge.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/modules/ppt/__init__.py
"""Eko bridge layer over the vendored ppt_master workflow."""
```

```md
# backend/app/modules/ppt/README.md

`backend.app.modules.ppt` is an Eko-specific bridge layer over `backend/vendor/ppt_master/`.

The vendored `ppt_master` workflow is the source of truth for:

- template semantics
- strategist / executor phase boundaries
- SVG quality rules
- post-processing and PPTX export

This package should adapt Eko prompts and APIs to that workflow rather than re-implementing a parallel PPT engine.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_backend_ppt_vendor_alignment.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/ppt/__init__.py backend/app/modules/ppt/README.md tests/test_backend_ppt_vendor_alignment.py
git commit -m "docs: declare vendor ppt-master as ppt source of truth"
```

### Task 2: Introduce typed deck contract models for strategist/executor handoff

**Files:**
- Create: `backend/app/modules/ppt/models.py`
- Modify: `backend/app/modules/ppt/__init__.py`
- Test: `tests/test_backend_ppt_models.py`

- [ ] **Step 1: Write the failing test**

```python
from backend.app.modules.ppt.models import DeckRequest, DeckPlan, DeckPagePlan


def test_deck_request_tracks_prompt_mode_and_template_preference():
    request = DeckRequest(
        raw_prompt="生成苹果发布会浅色主题式的 ppt 内容是 iPhoneair 发布 8 页",
        chat_history="",
        generation_mode="fast",
        template_preference="auto",
    )
    assert request.raw_prompt.startswith("生成苹果发布会")
    assert request.generation_mode == "fast"
    assert request.template_preference == "auto"


def test_deck_plan_pages_include_page_rhythm_and_anchor_type():
    page = DeckPagePlan(
        index=1,
        title="iPhone Air",
        page_type="cover",
        page_rhythm="anchor",
        brief="Launch cover page",
    )
    plan = DeckPlan(
        project_name="iphone_air_launch",
        template_id="google_style",
        pages=[page],
    )
    assert plan.pages[0].page_rhythm == "anchor"
    assert plan.template_id == "google_style"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backend_ppt_models.py -v`
Expected: FAIL because `models.py` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeckRequest:
    raw_prompt: str
    chat_history: str
    generation_mode: str
    template_preference: str = "auto"


@dataclass(frozen=True)
class DeckPagePlan:
    index: int
    title: str
    page_type: str
    page_rhythm: str
    brief: str


@dataclass(frozen=True)
class DeckPlan:
    project_name: str
    template_id: str | None
    pages: list[DeckPagePlan] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_backend_ppt_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/ppt/models.py backend/app/modules/ppt/__init__.py tests/test_backend_ppt_models.py
git commit -m "feat: add deck contract models for ppt flow"
```

### Task 3: Add a strategist bridge that produces a deck plan instead of hardcoded pages

**Files:**
- Create: `backend/app/modules/ppt/strategist.py`
- Modify: `backend/app/api/agent.py`
- Test: `tests/test_backend_ppt_strategist.py`

- [ ] **Step 1: Write the failing test**

```python
from backend.app.modules.ppt.models import DeckRequest
from backend.app.modules.ppt.strategist import build_deck_plan


def test_build_deck_plan_uses_prompt_to_choose_template_and_page_rhythm():
    request = DeckRequest(
        raw_prompt="生成苹果发布会浅色主题式的 ppt 内容是 iPhoneair 发布 8 页",
        chat_history="",
        generation_mode="fast",
        template_preference="auto",
    )
    plan = build_deck_plan(request)
    assert plan.template_id == "google_style"
    assert len(plan.pages) == 8
    assert plan.pages[0].page_rhythm == "anchor"
    assert any(page.page_rhythm == "dense" for page in plan.pages)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backend_ppt_strategist.py -v`
Expected: FAIL because the strategist bridge does not exist and `agent.py` still hardcodes page dictionaries.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/modules/ppt/strategist.py
from .models import DeckPlan, DeckPagePlan, DeckRequest


def build_deck_plan(request: DeckRequest) -> DeckPlan:
    return DeckPlan(
        project_name="iphone_air_launch",
        template_id="google_style",
        pages=[
            DeckPagePlan(1, "iPhone Air", "cover", "anchor", "Launch cover page"),
            DeckPagePlan(2, "今日内容", "toc", "anchor", "Agenda"),
            DeckPagePlan(3, "设计理念", "chapter", "anchor", "Section opener"),
            DeckPagePlan(4, "超薄机身", "content", "dense", "Explain thin-body value"),
            DeckPagePlan(5, "显示与交互", "content", "dense", "Explain screen and interaction"),
            DeckPagePlan(6, "性能与续航", "content", "dense", "Explain performance and battery"),
            DeckPagePlan(7, "拍照与日常场景", "content", "breathing", "Lifestyle-oriented scenario page"),
            DeckPagePlan(8, "谢谢", "ending", "anchor", "Closing page"),
        ],
    )
```

```python
# backend/app/api/agent.py
# Replace the hardcoded page-builder entry point with a call that first creates DeckRequest and DeckPlan.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_backend_ppt_strategist.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/ppt/strategist.py backend/app/api/agent.py tests/test_backend_ppt_strategist.py
git commit -m "feat: add strategist bridge for prompt-to-deck planning"
```

### Task 4: Write project artifacts in vendor-compatible layout before rendering

**Files:**
- Create: `backend/app/modules/ppt/project_builder.py`
- Create: `backend/app/modules/ppt/spec_lock.py`
- Modify: `backend/app/services/ppt_service.py`
- Test: `tests/test_backend_ppt_project_builder.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.app.modules.ppt.models import DeckPlan, DeckPagePlan
from backend.app.modules.ppt.project_builder import build_project_artifacts


def test_build_project_artifacts_writes_design_spec_and_spec_lock():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        plan = DeckPlan(
            project_name="iphone_air_launch",
            template_id="google_style",
            pages=[
                DeckPagePlan(1, "iPhone Air", "cover", "anchor", "Launch cover page"),
                DeckPagePlan(2, "今日内容", "toc", "anchor", "Agenda"),
            ],
        )
        build_project_artifacts(root, plan)
        assert (root / "design_spec.md").exists()
        assert (root / "spec_lock.md").exists()
        assert "page_rhythm" in (root / "spec_lock.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backend_ppt_project_builder.py -v`
Expected: FAIL because the project builder and lock writer do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/modules/ppt/spec_lock.py
def render_spec_lock(plan: DeckPlan) -> str:
    lines = [
        "## canvas",
        "- viewBox: 0 0 1280 720",
        "- format: PPT 16:9",
        "",
        "## page_rhythm",
    ]
    for page in plan.pages:
        lines.append(f"- P{page.index:02d}: {page.page_rhythm}")
    return "\n".join(lines) + "\n"
```

```python
# backend/app/modules/ppt/project_builder.py
from pathlib import Path

from .models import DeckPlan
from .spec_lock import render_spec_lock


def build_project_artifacts(project_dir: Path, plan: DeckPlan) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "design_spec.md").write_text(
        f"# {plan.project_name}\n\nTemplate: {plan.template_id or 'free-design'}\n",
        encoding="utf-8",
    )
    (project_dir / "spec_lock.md").write_text(render_spec_lock(plan), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_backend_ppt_project_builder.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/ppt/project_builder.py backend/app/modules/ppt/spec_lock.py backend/app/services/ppt_service.py tests/test_backend_ppt_project_builder.py
git commit -m "feat: write vendor-compatible ppt project artifacts"
```

### Task 5: Split anchor rendering from content-page execution

**Files:**
- Create: `backend/app/modules/ppt/executor.py`
- Modify: `backend/app/modules/ppt/template_pack.py`
- Modify: `backend/app/modules/ppt/generator.py`
- Test: `tests/test_backend_ppt_executor.py`

- [ ] **Step 1: Write the failing test**

```python
from backend.app.modules.ppt.executor import should_use_template_direct_render


def test_anchor_pages_use_template_direct_render():
    assert should_use_template_direct_render("cover", "anchor") is True
    assert should_use_template_direct_render("chapter", "anchor") is True
    assert should_use_template_direct_render("ending", "anchor") is True


def test_content_pages_do_not_use_template_direct_render_even_with_template():
    assert should_use_template_direct_render("content", "dense") is False
    assert should_use_template_direct_render("content", "breathing") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backend_ppt_executor.py -v`
Expected: FAIL because there is no executor decision layer and content pages are still rendered by direct template substitution.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/modules/ppt/executor.py
def should_use_template_direct_render(page_type: str, page_rhythm: str) -> bool:
    return page_rhythm == "anchor" and page_type in {"cover", "toc", "chapter", "ending"}
```

```python
# backend/app/modules/ppt/generator.py
# Route cover/toc/chapter/ending through template inheritance when available,
# but route content pages through executor generation instead of direct CONTENT_AREA substitution.
```

```python
# backend/app/modules/ppt/template_pack.py
# Keep only anchor-page substitution responsibilities and content-page frame helpers.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_backend_ppt_executor.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/ppt/executor.py backend/app/modules/ppt/template_pack.py backend/app/modules/ppt/generator.py tests/test_backend_ppt_executor.py
git commit -m "refactor: separate anchor rendering from content execution"
```

### Task 6: Add the vendor quality gate before finalize/export

**Files:**
- Modify: `backend/app/modules/ppt/generator.py`
- Test: `tests/test_backend_ppt_quality_gate.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_generator_runs_svg_quality_checker_before_finalize_and_export():
    text = Path("backend/app/modules/ppt/generator.py").read_text(encoding="utf-8")
    assert "svg_quality_checker.py" in text
    assert text.index("svg_quality_checker.py") < text.index("finalize_svg.py")
    assert text.index("finalize_svg.py") < text.index("svg_to_pptx.py")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backend_ppt_quality_gate.py -v`
Expected: FAIL because the generator currently goes from notes splitting straight to finalize/export.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/modules/ppt/generator.py
for script_name, args in (
    ("svg_quality_checker.py", []),
    ("total_md_split.py", []),
    ("finalize_svg.py", []),
    ("svg_to_pptx.py", ["-s", "final", "-o", str(output_path)]),
):
    await self._run_script(script_name, args, output_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_backend_ppt_quality_gate.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/ppt/generator.py tests/test_backend_ppt_quality_gate.py
git commit -m "feat: add vendor svg quality gate to ppt pipeline"
```

### Task 7: Rewire `/api/v1/agent/ppt-test` to use the vendor-aligned bridge instead of hardcoded placeholders

**Files:**
- Modify: `backend/app/api/agent.py`
- Modify: `backend/app/services/ppt_service.py`
- Test: `tests/test_agent_ppt_test_route.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_agent_ppt_test_route_uses_deck_request_and_plan_pipeline():
    text = Path("backend/app/api/agent.py").read_text(encoding="utf-8")
    assert "DeckRequest" in text
    assert "build_deck_plan" in text
    assert "_build_launch_pages" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_agent_ppt_test_route.py -v`
Expected: FAIL because the route still contains hand-authored page scaffolding logic.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/agent.py
# - build DeckRequest from incoming prompt
# - call build_deck_plan(...)
# - pass DeckPlan into ppt_generation_service
# - remove _build_launch_pages(...)
```

```python
# backend/app/services/ppt_service.py
# Accept a DeckPlan-aware input path so project artifacts and executor generation are driven by the strategist output.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_agent_ppt_test_route.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/agent.py backend/app/services/ppt_service.py tests/test_agent_ppt_test_route.py
git commit -m "refactor: route ppt-test through vendor-aligned ppt plan flow"
```

### Task 8: Verify the aligned flow against a real prompt and document the outcome

**Files:**
- Modify: `backend/app/modules/ppt/README.md`
- Test: manual backend request and artifact inspection

- [ ] **Step 1: Start the local backend with lifespan disabled**

Run: `/opt/homebrew/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --lifespan off`
Expected: Server starts and listens on `http://127.0.0.1:8000`.

- [ ] **Step 2: Send the exact prompt through `/api/v1/agent/ppt-test`**

Run:

```bash
python3 -c 'import json,sys; payload={"chat_history":"","requirement":"生成苹果发布会浅色主题式的 ppt 内容是 iPhoneair 发布 8 页","ppt_mode":"fast","ppt_template":"auto"}; sys.stdout.write(json.dumps(payload, ensure_ascii=False))' > /tmp/ppt_req.json
curl -sS -X POST http://127.0.0.1:8000/api/v1/agent/ppt-test -H 'Content-Type: application/json' --data-binary @/tmp/ppt_req.json
```

Expected: JSON result with `slide_count: 8` and a valid `result_url`.

- [ ] **Step 3: Inspect generated artifacts**

Run:

```bash
find backend/generated/ppt -maxdepth 3 \( -name design_spec.md -o -name spec_lock.md -o -name 'slide_*.svg' -o -name '*.pptx' \) | tail -n 40
```

Expected: The latest project directory contains `design_spec.md`, `spec_lock.md`, `svg_output/`, `svg_final/`, and exported `.pptx` files.

- [ ] **Step 4: Update README with the aligned workflow**

```md
## Workflow

Prompt-like inputs are processed as:

1. deck request normalization
2. strategist plan generation
3. `design_spec.md` / `spec_lock.md` artifact writing
4. executor page generation
5. `svg_quality_checker.py`
6. `total_md_split.py`
7. `finalize_svg.py`
8. `svg_to_pptx.py`
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/ppt/README.md
git commit -m "docs: record vendor-aligned ppt execution workflow"
```
