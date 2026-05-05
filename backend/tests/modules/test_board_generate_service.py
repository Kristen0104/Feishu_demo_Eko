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


class CapturingImportBoardClient(FeishuBoardClient):
    def __init__(self) -> None:
        super().__init__()
        self.captured_source = ""
        self.captured_syntax = ""
        self.captured_diagram_type = ""

    def import_diagram(self, whiteboard_id, *, source, source_type="file", syntax="plantuml", diagram_type="auto", style="board", user_access_token=None):  # type: ignore[no-untyped-def]
        self.captured_source = source
        self.captured_syntax = syntax
        self.captured_diagram_type = diagram_type
        return super().import_diagram(
            whiteboard_id,
            source=source,
            source_type=source_type,
            syntax=syntax,
            diagram_type=diagram_type,
            style=style,
            user_access_token=user_access_token,
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


def test_board_generate_service_uses_mermaid_sequence_source_for_sequence_diagram() -> None:
    board_client = CapturingImportBoardClient()
    service = BoardGenerateService(feishu_board_client=board_client)

    result = service.generate(
        message="请帮我画一个用户登录时序图",
        sharing_url="https://example.feishu.cn/wiki/board/wbcnSEQ",
    )

    assert result.render_mode == "import_diagram"
    assert board_client.captured_syntax == "mermaid"
    assert board_client.captured_diagram_type == "sequence"
    assert board_client.captured_source.startswith("sequenceDiagram")


def test_board_generate_service_generates_matching_import_sources_for_standard_diagrams() -> None:
    cases = [
        ("请帮我画一个用户注册流程图", "mermaid", "flowchart", "flowchart TD"),
        ("请帮我画一个用户登录时序图", "mermaid", "sequence", "sequenceDiagram"),
        ("请帮我画一个订单状态图", "mermaid", "state", "stateDiagram-v2"),
        ("请帮我画一个 RAG 模块类图", "mermaid", "class", "classDiagram"),
        ("请帮我画一个用户权限 ER 图", "mermaid", "er", "erDiagram"),
        ("请帮我画一个 AI 平台思维导图", "mermaid", "mindmap", "mindmap"),
        ("请帮我画一个销售占比饼图", "mermaid", "auto", "pie title"),
        ("请帮我画一个支付系统组件图", "plantuml", "component", "@startuml"),
        ("请帮我画一个审批活动图", "plantuml", "activity", "@startuml"),
    ]

    for message, expected_syntax, expected_diagram_type, expected_source_prefix in cases:
        board_client = CapturingImportBoardClient()
        result = BoardGenerateService(feishu_board_client=board_client).generate(
            message=message,
            sharing_url="https://example.feishu.cn/wiki/board/wbcnIMPORT",
        )

        assert result.render_mode == "import_diagram", message
        assert board_client.captured_syntax == expected_syntax, message
        assert board_client.captured_diagram_type == expected_diagram_type, message
        assert board_client.captured_source.startswith(expected_source_prefix), message


def test_board_generate_service_does_not_fallback_sequence_import_to_create_notes() -> None:
    class FailingImportBoardClient(FeishuBoardClient):
        def import_diagram(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("Feishu board request failed: HTTP 500")

    service = BoardGenerateService(feishu_board_client=FailingImportBoardClient())

    try:
        service.generate(
            message="请帮我画一个用户登录时序图",
            sharing_url="https://example.feishu.cn/wiki/board/wbcnSEQ",
        )
    except RuntimeError as exc:
        assert "标准图导入失败" in str(exc)
    else:
        raise AssertionError("Expected sequence import failure to be surfaced instead of downgraded")


def test_board_generate_service_does_not_fallback_any_import_diagram_to_create_notes() -> None:
    class FailingImportBoardClient(FeishuBoardClient):
        def import_diagram(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("Feishu board request failed: HTTP 500")

    service = BoardGenerateService(feishu_board_client=FailingImportBoardClient())

    try:
        service.generate(
            message="帮我画一个用户注册流程图",
            sharing_url="https://example.feishu.cn/wiki/board/wbcnFLOW",
        )
    except RuntimeError as exc:
        assert "标准图导入失败" in str(exc)
    else:
        raise AssertionError("Expected import failure to be surfaced instead of downgraded")


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


def test_board_generate_service_create_notes_matrix_covers_all_precise_diagram_types() -> None:
    cases = [
        "帮我画一个 AI 网关架构图",
        "请帮我画一个 AI 团队组织架构图",
        "请生成一个客户旅程树图",
        "做一个竞品能力对比矩阵",
        "做一个项目推进看板",
        "做一个用户流失原因鱼骨图",
        "做一个销售额柱状图",
        "做一个活跃用户折线图",
        "做一个自定义精排图，要求节点精确定位",
    ]

    for message in cases:
        result = BoardGenerateService(feishu_board_client=FeishuBoardClient()).generate(
            message=message,
            sharing_url="https://example.feishu.cn/wiki/board/wbcnCREATE",
        )

        assert result.render_mode == "create_notes", message
        assert len(result.node_ids) >= 6, message
        assert result.preview_url == "https://stub.preview/wbcnCREATE.png"


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


def test_board_generate_service_normalizes_fishbone_when_llm_plan_is_invalid() -> None:
    class StubBoardClient(FeishuBoardClient):
        def __init__(self):
            super().__init__()
            self.visible_node_ids: list[str] = []

        def create_notes(self, whiteboard_id, nodes_json_or_nodes, source_type="content", client_token="", user_id_type="open_id"):
            node_ids = [f"node-{len(self.visible_node_ids) + index}" for index, _ in enumerate(nodes_json_or_nodes)]
            self.visible_node_ids.extend(node_ids)
            return {
                "node_ids": node_ids,
                "failed_items": [],
            }

        def get_board_nodes(self, whiteboard_id):
            return {"data": {"nodes": [{"id": node_id} for node_id in self.visible_node_ids]}}

        def get_board_image(self, whiteboard_id):
            return {"preview_url": f"https://stub.preview/{whiteboard_id}.png"}

    class StubLlmClient:
        def is_configured(self) -> bool:
            return True

        def complete(self, *, system_prompt: str, user_prompt: str) -> str:
            return "not-json"

    service = BoardGenerateService(
        feishu_board_client=StubBoardClient(),
        llm_client=StubLlmClient(),  # type: ignore[arg-type]
    )

    result = service.generate(
        message="请生成一张AI平台项目延期原因分析鱼骨图，主因包括需求变更、数据准备、模型效果、工程稳定性、资源协调、验收流程。",
        sharing_url="https://example.feishu.cn/wiki/board/wbcnFISH",
    )

    assert result.render_mode == "create_notes"
    assert result.whiteboard_id == "wbcnFISH"
    assert len(result.node_ids) == 21
    assert any("shape_count=15 connector_count=6" in log for _, log in result.execution_logs)


def test_board_generate_service_replaces_sparse_llm_plan() -> None:
    class StubLlmClient:
        def is_configured(self) -> bool:
            return True

        def complete(self, *, system_prompt: str, user_prompt: str) -> str:
            return '{"title":"营销新产品思路图","layout":"tree","groups":[{"title":"中心","root":"根节点","children":[]}],"edges":[]}'

    service = BoardGenerateService(
        feishu_board_client=FeishuBoardClient(),
        llm_client=StubLlmClient(),  # type: ignore[arg-type]
    )

    result = service.generate(
        message="生成一个营销新产品的思路图吧",
        sharing_url="https://example.feishu.cn/wiki/board/wbcnIDEA",
    )

    assert result.render_mode == "create_notes"
    assert len(result.node_ids) >= 15
    assert any("内容过少" in message for _, message in result.execution_logs)


def test_board_generate_service_fails_when_created_nodes_stay_invisible() -> None:
    class InvisibleBoardClient(FeishuBoardClient):
        def create_notes(self, whiteboard_id, nodes_json_or_nodes, source_type="content", client_token="", user_id_type="open_id"):
            return {"node_ids": [f"node-{index}" for index, _ in enumerate(nodes_json_or_nodes)]}

        def get_board_nodes(self, whiteboard_id):
            return {"data": {"nodes": []}}

    service = BoardGenerateService(feishu_board_client=InvisibleBoardClient())
    service._VISIBILITY_WAIT_SECONDS = 0

    try:
        service.generate(
            message="生成一个营销新产品的思路图吧",
            sharing_url="https://example.feishu.cn/wiki/board/wbcnEMPTY",
        )
    except RuntimeError as exc:
        assert "画板节点写入后数量异常" in str(exc)
    else:
        raise AssertionError("Expected invisible board nodes to fail generation")


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
