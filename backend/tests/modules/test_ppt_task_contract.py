from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import container
from app.modules.ppt.dependencies import get_ppt_service
from app.modules.ppt.repository import PptRepository
from app.modules.ppt.schemas import PptTaskCreateRequest
from app.modules.ppt.service import PptService


def _build_client() -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    return TestClient(app)


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


def _build_client_with_export_stub(tmp_path) -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    export_stub = StubPptxExportService()
    stub_service = PptService(
        repository=PptRepository(),
        generate_service=StubPptHtmlGenerateService(),
        export_service=export_stub,
        generated_root=tmp_path,
    )
    app.dependency_overrides[get_ppt_service] = lambda: stub_service
    app.state.export_stub = export_stub
    return TestClient(app)


def test_create_ppt_task_returns_pending_html_task() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/ppt/tasks",
        json={
            "topic": "AI 工作流",
            "prompt": "生成一份杂志风 HTML PPT",
            "title": "AI 工作流杂志风分享",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["message"] == "success"
    assert payload["data"]["topic"] == "AI 工作流"
    assert payload["data"]["prompt"] == "生成一份杂志风 HTML PPT"
    assert payload["data"]["title"] == "AI 工作流杂志风分享"
    assert payload["data"]["status"] == "pending"
    assert payload["data"]["current_step"] == "pending"
    assert payload["data"]["artifact_kind"] == "html"
    assert payload["data"]["artifact_path"] is None
    assert payload["data"]["preview_url"].endswith(
        f'/api/v1/ppt/tasks/{payload["data"]["task_id"]}/preview'
    )
    assert payload["data"]["logs"] == []


def test_get_ppt_task_returns_latest_task_state() -> None:
    client = _build_client()

    create_response = client.post(
        "/api/v1/ppt/tasks",
        json={
            "topic": "AI 产品发布",
            "prompt": "生成完整 HTML deck",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    response = client.get(f"/api/v1/ppt/tasks/{task_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["task_id"] == task_id
    assert payload["data"]["topic"] == "AI 产品发布"
    assert payload["data"]["prompt"] == "生成完整 HTML deck"
    assert payload["data"]["status"] == "pending"
    assert payload["data"]["artifact_kind"] == "html"


def test_run_ppt_task_returns_html_task_contract() -> None:
    client = _build_client()

    create_response = client.post(
        "/api/v1/ppt/tasks",
        json={
            "topic": "AI 创作者经济",
            "prompt": "生成单文件 HTML 演讲稿",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    response = client.post(f"/api/v1/ppt/tasks/{task_id}/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["task_id"] == task_id
    assert payload["data"]["artifact_kind"] == "html"
    assert payload["data"]["status"] in {"pending", "running", "succeeded"}


def test_run_ppt_task_schedules_background_pptx_export(tmp_path) -> None:
    client = _build_client_with_export_stub(tmp_path)

    create_response = client.post(
        "/api/v1/ppt/tasks",
        json={
            "topic": "AI 创作者经济",
            "prompt": "生成单文件 HTML 演讲稿",
            "title": "AI 创作者经济",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    response = client.post(f"/api/v1/ppt/tasks/{task_id}/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "succeeded"
    assert payload["data"]["pptx_status"] == "pending"

    latest = client.get(f"/api/v1/ppt/tasks/{task_id}").json()["data"]
    assert latest["pptx_status"] == "succeeded"
    assert latest["pptx_download_url"].endswith(f"/api/v1/ppt/tasks/{task_id}/download-pptx")
    assert client.app.state.export_stub.calls == 1


def test_preview_endpoint_serves_generated_html() -> None:
    client = _build_client()

    create_response = client.post(
        "/api/v1/ppt/tasks",
        json={
            "topic": "AI 创作者经济",
            "prompt": "生成单文件 HTML 演讲稿",
            "title": "AI 创作者经济",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    run_response = client.post(f"/api/v1/ppt/tasks/{task_id}/run")
    assert run_response.status_code == 200

    response = client.get(f"/api/v1/ppt/tasks/{task_id}/preview")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<!DOCTYPE html>" in response.text


def test_export_pptx_updates_task_with_download_contract(tmp_path) -> None:
    client = _build_client_with_export_stub(tmp_path)

    create_response = client.post(
        "/api/v1/ppt/tasks",
        json={
            "topic": "AI 创作者经济",
            "prompt": "生成单文件 HTML 演讲稿",
            "title": "AI 创作者经济",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    run_response = client.post(f"/api/v1/ppt/tasks/{task_id}/run")
    assert run_response.status_code == 200

    export_response = client.post(f"/api/v1/ppt/tasks/{task_id}/export-pptx")

    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["code"] == 0
    assert payload["data"]["task_id"] == task_id
    assert payload["data"]["pptx_path"].endswith("deck.pptx")
    assert payload["data"]["pptx_download_url"].endswith(
        f"/api/v1/ppt/tasks/{task_id}/download-pptx"
    )


def test_download_pptx_endpoint_serves_generated_file(tmp_path) -> None:
    client = _build_client_with_export_stub(tmp_path)

    create_response = client.post(
        "/api/v1/ppt/tasks",
        json={
            "topic": "AI 创作者经济",
            "prompt": "生成单文件 HTML 演讲稿",
            "title": "AI 创作者经济",
        },
    )
    task_id = create_response.json()["data"]["task_id"]

    client.post(f"/api/v1/ppt/tasks/{task_id}/run")
    client.post(f"/api/v1/ppt/tasks/{task_id}/export-pptx")

    response = client.get(f"/api/v1/ppt/tasks/{task_id}/download-pptx")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert response.content == b"stub-pptx"
