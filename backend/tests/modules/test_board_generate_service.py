from __future__ import annotations

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import CanvasBoardTaskCreateRequest
from app.modules.canvas.service import CanvasService
from app.modules.feishu.board_client import FeishuBoardClient
from app.services.board_generate_service import (
    BoardGenerateResult,
    BoardGenerateService,
    _extract_json_object,
    extract_embedded_diagram_source,
)


def test_board_generate_service_uses_import_path_for_flowchart() -> None:
    service = BoardGenerateService(feishu_board_client=FeishuBoardClient())

    result = service.generate(
        message="帮我画一个用户注册流程图",
        sharing_url="https://example.feishu.cn/wiki/board/wbcnFLOW",
    )

    assert result.whiteboard_id == "wbcnFLOW"
    assert result.render_mode == "import_diagram"
    assert result.preview_url == "https://stub.preview/wbcnFLOW.png"
    assert "import_diagram" in result.result_summary


def test_board_generate_service_infers_sequence_diagram_type() -> None:
    service = BoardGenerateService(feishu_board_client=FeishuBoardClient())

    result = service.generate(
        message="请帮我画一个用户登录时序图",
        sharing_url="https://example.feishu.cn/wiki/board/wbcnSEQ",
    )

    assert result.render_mode == "import_diagram"
    assert result.ticket_id == "ticket-wbcnSEQ"


def test_board_generate_service_uses_embedded_mermaid_without_llm() -> None:
    service = BoardGenerateService(feishu_board_client=FeishuBoardClient())

    result = service.generate(
        message="请直接导入这个 Mermaid\n```mermaid\nflowchart TD\nA-->B\n```",
        sharing_url="https://example.feishu.cn/wiki/board/wbcnMMD",
    )

    assert result.render_mode == "import_diagram"
    assert any("直接导入" in log for _, log in result.execution_logs)


def test_board_generate_service_uses_create_notes_for_architecture() -> None:
    service = BoardGenerateService(feishu_board_client=FeishuBoardClient())

    result = service.generate(
        message="帮我画一个 AI 网关架构图",
        sharing_url="https://example.feishu.cn/wiki/board/wbcnARCH",
    )

    assert result.whiteboard_id == "wbcnARCH"
    assert result.render_mode == "create_notes"
    assert result.preview_url == "https://stub.preview/wbcnARCH.png"
    assert "create_notes" in result.result_summary
    assert len(result.node_ids) >= 10


def test_board_generate_service_keeps_valid_llm_plan_instead_of_forcing_fallback() -> None:
    class StubLlmClient:
        def is_configured(self) -> bool:
            return True

        def complete(self, *, system_prompt: str, user_prompt: str) -> str:
            return (
                '{"title":"组织结构图","layout":"tree","groups":[{"title":"组织结构","root":"研发负责人",'
                '"children":["产品线","技术线"],"child_groups":[{"parent":"产品线","children":["产品团队","设计团队"]},'
                '{"parent":"技术线","children":["前端团队","后端团队"]}]}],"edges":['
                '{"from":"g0n0","to":"g1n0","direction":"tb"},'
                '{"from":"g0n0","to":"g1n1","direction":"tb"},'
                '{"from":"g1n0","to":"g2n0_0","direction":"tb","shape":"right_angled_polyline"},'
                '{"from":"g1n0","to":"g2n0_1","direction":"tb","shape":"right_angled_polyline"}]}'
            )

    service = BoardGenerateService(
        feishu_board_client=FeishuBoardClient(),
        llm_client=StubLlmClient(),  # type: ignore[arg-type]
    )

    result = service.generate(
        message="帮我画一个完整详细的 AI 产品研发组织架构图",
        sharing_url="https://example.feishu.cn/wiki/board/wbcnORG",
    )

    assert result.render_mode == "create_notes"
    assert result.whiteboard_id == "wbcnORG"
    assert 8 <= len(result.node_ids) <= 20


def test_canvas_service_run_board_task_updates_task_state() -> None:
    repository = CanvasRepository()
    generator = BoardGenerateService(feishu_board_client=FeishuBoardClient())
    service = CanvasService(repository=repository, board_generate_service=generator)

    task = service.create_board_task(
        CanvasBoardTaskCreateRequest(
            message="帮我画一个 AI 网关架构图",
            sharing_url="https://example.feishu.cn/wiki/board/wbcnARCH",
        )
    )

    completed = service.run_board_task(task.task_id)

    assert completed.status == "succeeded"
    assert completed.current_step == "succeeded"
    assert completed.whiteboard_id == "wbcnARCH"
    assert completed.render_mode == "create_notes"
    assert completed.preview_url == "https://stub.preview/wbcnARCH.png"
    assert len(completed.node_ids) >= 10
    assert any(log.step == "planning" for log in completed.logs)
    assert any("已创建" in log.message for log in completed.logs)


def test_board_generate_service_resolves_document_sharing_url() -> None:
    service = BoardGenerateService(feishu_board_client=FeishuBoardClient())

    result = service.generate(
        message="帮我画一个 AI 网关架构图",
        sharing_url="https://example.feishu.cn/docx/AbCdEfGhIjKl",
    )

    assert result.whiteboard_id == "resolved-from-AbCdEfGhIjKl"
    assert result.render_mode == "create_notes"


def test_extract_embedded_diagram_source_supports_fences_and_raw_plantuml() -> None:
    fenced = extract_embedded_diagram_source("```mermaid\nflowchart TD\nA-->B\n```")
    plantuml = extract_embedded_diagram_source("before\n@startuml\nA->B\n@enduml\nafter")

    assert fenced == ("mermaid", "flowchart TD\nA-->B")
    assert plantuml == ("plantuml", "@startuml\nA->B\n@enduml")


def test_extract_json_object_recovers_json_from_fenced_or_wrapped_content() -> None:
    fenced = _extract_json_object('```json\n{"title":"A","groups":[]}\n```')
    wrapped = _extract_json_object('Here is the plan:\n{"title":"B","groups":[]}\nDone.')

    assert fenced == '{"title":"A","groups":[]}'
    assert wrapped == '{"title":"B","groups":[]}'


def test_canvas_service_marks_task_failed_when_generation_raises() -> None:
    class FailingBoardGenerateService:
        def generate(self, *, message: str, sharing_url: str) -> BoardGenerateResult:  # type: ignore[override]
            raise RuntimeError("mock generation failed")

    repository = CanvasRepository()
    service = CanvasService(repository=repository, board_generate_service=FailingBoardGenerateService())  # type: ignore[arg-type]

    task = service.create_board_task(
        CanvasBoardTaskCreateRequest(
            message="帮我画一个 AI 网关架构图",
            sharing_url="https://example.feishu.cn/wiki/board/wbcnARCH",
        )
    )

    failed = service.run_board_task(task.task_id)

    assert failed.status == "failed"
    assert failed.current_step == "failed"
    assert failed.error_message == "mock generation failed"
    assert failed.logs[-1].step == "failed"
