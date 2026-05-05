from __future__ import annotations

import pytest

from app.board_renderer.create_notes import choose_layout_mode
from app.services.board_generate_service import choose_render_mode


@pytest.mark.parametrize(
    ("message", "expected_mode"),
    [
        ("请帮我画一个用户注册流程图", "import_diagram"),
        ("请帮我画一个订单处理时序图", "import_diagram"),
        ("请帮我画一个 RAG 模块类图", "import_diagram"),
        ("请帮我画一个订单状态图", "import_diagram"),
        ("请帮我画一个用户权限 ER 图", "import_diagram"),
        ("请帮我画一个支付系统组件图", "import_diagram"),
        ("请帮我画一个审批活动图", "import_diagram"),
        ("请帮我画一个 AI 平台思维导图", "import_diagram"),
        ("请帮我画一个销售占比饼图", "import_diagram"),
        ("请帮我画一个 RAG 系统架构图", "create_notes"),
        ("请帮我画一个 AI 团队组织架构图", "create_notes"),
        ("请生成一个客户旅程树图", "create_notes"),
        ("做一个竞品能力对比矩阵", "create_notes"),
        ("做一个项目推进看板", "create_notes"),
        ("做一个用户流失原因鱼骨图", "create_notes"),
        ("做一个销售额柱状图", "create_notes"),
        ("做一个活跃用户折线图", "create_notes"),
        ("做一个自定义精排图，要求节点精确定位", "create_notes"),
    ],
)
def test_choose_render_mode_covers_board_diagram_matrix(message: str, expected_mode: str) -> None:
    assert choose_render_mode(message) == expected_mode


@pytest.mark.parametrize(
    ("message", "expected_layout"),
    [
        ("请帮我画一个 RAG 系统架构图", "layered"),
        ("请帮我画一个 AI 团队组织架构图", "tree"),
        ("请生成一个客户旅程树图", "tree"),
        ("做一个竞品能力对比矩阵", "matrix"),
        ("做一个项目推进看板", "matrix"),
        ("做一个用户流失原因鱼骨图", "free"),
        ("做一个销售额柱状图", "free"),
        ("做一个活跃用户折线图", "free"),
    ],
)
def test_choose_layout_mode_covers_create_notes_diagram_matrix(message: str, expected_layout: str) -> None:
    assert choose_layout_mode(message) == expected_layout


def test_choose_render_mode_prefers_import_for_flowchart() -> None:
    assert choose_render_mode("请帮我画一个用户注册流程图") == "import_diagram"


def test_choose_render_mode_prefers_import_for_explicit_mermaid() -> None:
    assert choose_render_mode("graph TD; A-->B; B-->C") == "import_diagram"


def test_choose_render_mode_prefers_import_for_sequence_diagram() -> None:
    assert choose_render_mode("请帮我画一个订单处理时序图") == "import_diagram"


def test_choose_render_mode_prefers_import_for_class_diagram() -> None:
    assert choose_render_mode("请帮我画一个 RAG 模块类图") == "import_diagram"


def test_choose_render_mode_prefers_import_for_mindmap() -> None:
    assert choose_render_mode("请帮我画一个 AI 平台思维导图") == "import_diagram"


def test_choose_render_mode_prefers_import_for_explicit_plantuml() -> None:
    assert choose_render_mode("@startuml\nAlice -> Bob: Hello\n@enduml") == "import_diagram"


def test_choose_render_mode_prefers_create_notes_for_architecture() -> None:
    assert choose_render_mode("请帮我画一个 RAG 系统架构图") == "create_notes"


def test_choose_render_mode_prefers_create_notes_for_org_chart() -> None:
    assert choose_render_mode("请帮我画一个 AI 团队组织架构图") == "create_notes"


def test_choose_render_mode_prefers_create_notes_for_matrix() -> None:
    assert choose_render_mode("做一个竞品能力对比矩阵") == "create_notes"


def test_choose_render_mode_prefers_create_notes_for_fishbone() -> None:
    assert choose_render_mode("做一个用户流失原因鱼骨图") == "create_notes"


def test_choose_render_mode_prefers_create_notes_for_custom_precise_diagram() -> None:
    assert choose_render_mode("做一个自定义精排图，要求节点精确定位") == "create_notes"


def test_choose_render_mode_prefers_create_notes_for_tree_diagram() -> None:
    assert choose_render_mode("请生成一个客户旅程树图") == "create_notes"
