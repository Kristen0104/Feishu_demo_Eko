from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.modules.ppt.repository import PptRepository
from app.modules.ppt.schemas import PptTaskCreateRequest
from app.modules.ppt.service import PptService
from app.services.ppt_html_generate_service import PptHtmlGenerateService
from app.services.pptx_export_service import PptxExportService


class StubPptHtmlGenerateService:
    def generate_html(self, *, topic: str, prompt: str, title: str | None = None) -> str:
        page_title = title or topic
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{page_title}</title>
</head>
<body>
  <div id="deck">
    <section class="slide hero dark">
      <h1 data-anim>{topic}</h1>
      <p data-anim>{prompt}</p>
    </section>
  </div>
</body>
</html>
"""


class StubPptxExportService:
    def __init__(self) -> None:
        self.calls = 0

    def export(self, *, html_path, output_dir, deck_title):
        self.calls += 1
        output_dir.mkdir(parents=True, exist_ok=True)
        pptx_path = output_dir / "deck.pptx"
        pptx_path.write_bytes(b"stub-pptx")
        return {
            "pptx_path": str(pptx_path),
            "slide_image_paths": [],
        }


class StubAssets:
    def load(self) -> dict[str, str]:
        template = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>[必填] 替换为 PPT 标题 · Deck Title</title></head>
<body><div id="deck"><section class="slide hero dark"><h1 data-anim>Title</h1></section></div></body>
</html>
"""
        return {
            "skill_md": "guizang-ppt-skill",
            "license_text": "MIT License",
            "template_html": template,
            "layouts_md": "layouts",
            "themes_md": "themes",
            "components_md": "components",
            "checklist_md": "checklist",
            "motion_js": "motion",
        }


class StubLiveLlmClient:
    def __init__(self) -> None:
        self.timeout: float | None = None
        self.max_tokens: int | None = None
        self.user_prompt: str | None = None

    def is_configured(self) -> bool:
        return True

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 60,
        max_tokens: int | None = None,
    ) -> str:
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.user_prompt = user_prompt
        return """
<section class="slide hero dark">
  <div class="chrome"><div>AI Workflow</div><div>01 / 06</div></div>
  <div class="frame" style="display:grid; gap:4vh; align-content:center; min-height:80vh">
    <div class="kicker" data-anim>Opening</div>
    <h1 class="h-hero" data-anim>Live</h1>
    <p class="lead" data-anim>Intro</p>
  </div>
  <div class="foot"><div>Foot</div><div>—</div></div>
</section>
"""


class StubBrokenMarkupLlmClient(StubLiveLlmClient):
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 60,
        max_tokens: int | None = None,
    ) -> str:
        self.timeout = timeout
        self.max_tokens = max_tokens
        return """
<section class="slide light">
  <div class="chrome"><div>Core Specs</div><div>02 / 07</div></div>
  <div class="frame">
    <div class="grid-4">
      <div class="stat-card">
        <div class="stat-label">Avg Duration</div>
        <div class="stat-note>占前端开发总时长35%</div>
      </div>
    </div>
  </div>
</section>
"""


def test_ppt_service_run_task_persists_generated_html(tmp_path: Path) -> None:
    service = PptService(
        repository=PptRepository(),
        generate_service=StubPptHtmlGenerateService(),
        generated_root=tmp_path,
    )

    created = service.create_task(
        PptTaskCreateRequest(
            topic="AI 杂志风演讲",
            prompt="生成一份单文件 HTML deck",
            title="AI 杂志风演讲",
        )
    )

    completed = service.run_task(created.task_id)

    assert completed.status == "succeeded"
    assert completed.current_step == "succeeded"
    assert completed.preview_url == f"/api/v1/ppt/tasks/{created.task_id}/preview"
    assert completed.artifact_path is not None
    artifact_path = Path(completed.artifact_path)
    assert artifact_path.exists() is True
    assert artifact_path.name == "index.html"
    assert "<!DOCTYPE html>" in artifact_path.read_text(encoding="utf-8")


def test_ppt_service_export_pptx_persists_artifact(tmp_path: Path) -> None:
    export_stub = StubPptxExportService()
    service = PptService(
        repository=PptRepository(),
        generate_service=StubPptHtmlGenerateService(),
        export_service=export_stub,
        generated_root=tmp_path,
    )

    created = service.create_task(
        PptTaskCreateRequest(
            topic="AI 杂志风演讲",
            prompt="生成一份单文件 HTML deck",
            title="AI 杂志风演讲",
        )
    )
    service.run_task(created.task_id)

    exported = service.export_pptx(created.task_id)

    assert exported.pptx_path is not None
    assert exported.pptx_download_url == f"/api/v1/ppt/tasks/{created.task_id}/download-pptx"
    pptx_path = Path(exported.pptx_path)
    assert pptx_path.exists() is True
    assert pptx_path.name == "deck.pptx"
    assert export_stub.calls == 1


def test_ppt_html_generate_service_uses_extended_timeout_in_live_mode() -> None:
    llm_client = StubLiveLlmClient()
    service = PptHtmlGenerateService(
        assets=StubAssets(),
        llm_client=llm_client,
        allow_live_llm=True,
    )

    html = service.generate_html(
        topic="AI 杂志风演讲",
        prompt="生成一份单文件 HTML deck",
        title="AI 杂志风演讲",
    )

    assert "<!DOCTYPE html>" in html
    assert "<title>AI 杂志风演讲</title>" in html
    assert 'id="deck"' in html
    assert '<section class="slide hero dark">' in html
    assert llm_client.timeout == 180
    assert llm_client.max_tokens == 16000
    assert "Output 8-10 complete" in llm_client.user_prompt


def test_ppt_html_generate_service_injects_slide_markup_into_template() -> None:
    llm_client = StubLiveLlmClient()
    service = PptHtmlGenerateService(
        assets=StubAssets(),
        llm_client=llm_client,
        allow_live_llm=True,
    )

    html = service.generate_html(
        topic="AI 协作工作流",
        prompt="生成 6 页 HTML PPT",
        title="AI 协作工作流",
    )

    assert "[必填]" not in html
    assert "<title>AI 协作工作流</title>" in html
    assert '<div id="deck">' in html
    assert 'class="slide hero dark"' in html
    assert "Live" in html


def test_ppt_html_generate_service_respects_user_requested_slide_count() -> None:
    llm_client = StubLiveLlmClient()
    service = PptHtmlGenerateService(
        assets=StubAssets(),
        llm_client=llm_client,
        allow_live_llm=True,
    )

    service.generate_html(
        topic="AI 协作工作流",
        prompt="做一份 12 页的 HTML PPT，讲清楚协作工作流。",
        title="AI 协作工作流",
    )

    assert "Output exactly the user-requested slide count: 12 complete" in llm_client.user_prompt


def test_ppt_html_generate_service_repairs_unclosed_class_attribute() -> None:
    service = PptHtmlGenerateService(
        assets=StubAssets(),
        llm_client=StubBrokenMarkupLlmClient(),
        allow_live_llm=True,
    )

    html = service.generate_html(
        topic="前端联调实跑",
        prompt="生成 6 页 HTML PPT",
        title="前端联调实跑",
    )

    assert 'class="stat-note">' in html
    assert 'class="stat-note>占前端开发总时长35%' not in html


def test_pptx_export_service_passes_device_scale_factor(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd, capture_output, text, env, check):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps(
                {
                    "pptxPath": str(tmp_path / "out" / "deck.pptx"),
                    "slideImagePaths": [],
                }
            ),
            stderr="",
        )

    monkeypatch.setattr("app.services.pptx_export_service.subprocess.run", fake_run)

    html_path = tmp_path / "index.html"
    html_path.write_text("<!DOCTYPE html><html><body></body></html>", encoding="utf-8")
    service = PptxExportService(
        viewport_width=1600,
        viewport_height=900,
        device_scale_factor=2,
        script_path=tmp_path / "export_html_to_pptx.mjs",
    )

    service.export(
        html_path=html_path,
        output_dir=tmp_path / "out",
        deck_title="Demo",
    )

    assert "--device-scale-factor" in captured["cmd"]
    scale_index = captured["cmd"].index("--device-scale-factor")
    assert captured["cmd"][scale_index + 1] == "2"
