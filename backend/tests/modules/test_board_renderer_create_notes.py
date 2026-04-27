from __future__ import annotations

import pytest

from app.board_renderer.create_notes import (
    BOARD_RENDERER_SCHEMA_RULES,
    BOARD_RENDERER_TYPOGRAPHY_RULES,
    CREATE_NOTES_RULE_SUMMARY,
    build_connectors_from_mapping,
    build_create_notes_payload,
    build_background_region,
    build_connector,
    build_layered_row_positions,
    build_matrix_positions,
    build_shape_node,
    build_tree_child_positions,
    choose_layout_mode,
    choose_text_alignment,
    estimate_node_size,
    estimate_text_layout,
    fallback_plan_from_message,
    infer_palette_name,
    get_palette,
    normalize_create_notes_plan,
    parse_create_notes_plan,
)


def test_palette_constants_match_reference_classic_rules() -> None:
    palette = get_palette("classic")

    assert palette["groups"][0]["fill_color"] == "#F0F4FC"
    assert palette["groups"][0]["border_color"] == "#5178C6"
    assert palette["line_color"] == "#BBBFC4"
    assert BOARD_RENDERER_TYPOGRAPHY_RULES["title"]["font_size"] == 24
    assert BOARD_RENDERER_SCHEMA_RULES["shape_node_fields"][0] == "type"
    assert "absolute coordinates" in CREATE_NOTES_RULE_SUMMARY
    assert "Estimate node size" in CREATE_NOTES_RULE_SUMMARY


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("帮我做一个竞品能力对比矩阵", "matrix"),
        ("请画组织架构图", "tree"),
        ("做一个微服务系统拓扑", "island"),
        ("画一个鱼骨图分析问题", "free"),
        ("画一个 RAG 系统架构图", "layered"),
    ],
)
def test_choose_layout_mode_translates_reference_rules(message: str, expected: str) -> None:
    assert choose_layout_mode(message) == expected


def test_build_shape_node_uses_safe_schema_and_palette_border() -> None:
    node = build_shape_node("用户服务", x=100, y=120, group_index=2)

    assert set(node) == set(BOARD_RENDERER_SCHEMA_RULES["shape_node_fields"])
    assert node["style"]["fill_color"] == "#FFFFFF"
    assert node["style"]["border_color"] == "#509863"
    assert node["text"]["font_size"] == 14
    assert node["text"]["horizontal_align"] == "center"


def test_build_shape_node_uses_dark_palette_fill_for_tech_theme() -> None:
    node = build_shape_node("API 网关", x=100, y=120, palette="tech", group_index=1)

    assert node["style"]["fill_color"] == "#1E293B"
    assert node["style"]["border_color"] == "#3B82F6"
    assert node["text"]["horizontal_align"] == "center"


def test_build_background_region_uses_low_opacity_group_band() -> None:
    region = build_background_region(
        "服务层",
        x=50,
        y=80,
        width=700,
        height=180,
        group_index=0,
    )

    assert region["z_index"] == 0
    assert region["style"]["fill_color"] == "#F0F4FC"
    assert region["style"]["fill_opacity"] == 25
    assert region["style"]["border_width"] == "narrow"
    assert region["text"]["text"] == ""


@pytest.mark.parametrize(
    ("text", "expected_size", "expected_align"),
    [
        ("用户", (120, 44), ("center", "mid")),
        ("用户服务", (120, 44), ("center", "mid")),
        ("用户服务管理", (160, 44), ("center", "mid")),
        ("用户服务注册登录和权限管理", (180, 64), ("center", "mid")),
        ("用户服务注册登录和权限管理系统模块", (200, 80), ("left", "mid")),
        ("标题\n说明", (180, 64), ("left", "top")),
    ],
)
def test_text_layout_rules_follow_reference_buckets(
    text: str,
    expected_size: tuple[int, int],
    expected_align: tuple[str, str],
) -> None:
    assert estimate_node_size(text) == expected_size
    assert choose_text_alignment(text) == expected_align
    layout = estimate_text_layout(text)
    assert layout["width"] == expected_size[0]
    assert layout["height"] == expected_size[1]


def test_build_connector_uses_direction_map_and_fanout_positions() -> None:
    connector = build_connector(
        "node-a",
        "node-b",
        direction="tb",
        source_slot=1,
        source_total=3,
        target_slot=0,
        target_total=2,
    )

    start = connector["connector"]["start"]["attached_object"]
    end = connector["connector"]["end"]["attached_object"]

    assert connector["style"]["border_color"] == "#BBBFC4"
    assert start["snap_to"] == "bottom"
    assert start["position"] == {"x": 0.5, "y": 1}
    assert end["snap_to"] == "top"
    assert end["position"] == {"x": 0.333, "y": 0}


def test_layout_position_helpers_follow_reference_spacing() -> None:
    assert build_layered_row_positions(3) == [(100, 80), (320, 80), (540, 80)]
    assert build_matrix_positions(2, 2) == [[(100, 80), (270, 80)], [(100, 135), (270, 135)]]
    assert build_tree_child_positions(300, 200, 3) == [(80, 170), (320, 170), (560, 170)]


def test_fallback_plan_and_payload_follow_create_notes_contract() -> None:
    plan = fallback_plan_from_message("帮我画一个 AI 网关架构图")
    shape_entries, connector_entries = build_create_notes_payload(plan)

    assert plan["layout"] == "layered"
    assert shape_entries
    assert connector_entries
    assert shape_entries[0]["key"] == "title"
    assert shape_entries[1]["key"].startswith("bg")
    first_node = next(entry["node"] for entry in shape_entries if entry["key"] == "g0n0")
    assert first_node["x"] >= 0
    assert first_node["y"] >= 0
    assert first_node["width"] >= 120
    assert first_node["style"]["border_width"] == "medium"
    assert "\n" in first_node["text"]["text"]


def test_layered_section_label_sits_inside_background_with_top_padding() -> None:
    plan = fallback_plan_from_message("帮我画一个 AI 网关架构图")
    shape_entries, _ = build_create_notes_payload(plan)
    background = next(entry["node"] for entry in shape_entries if entry["key"] == "bg0")
    label = next(entry["node"] for entry in shape_entries if entry["key"] == "label0")
    first_node = next(entry["node"] for entry in shape_entries if entry["key"] == "g0n0")

    assert label["x"] >= background["x"]
    assert label["y"] >= background["y"] + 12
    assert label["x"] + label["width"] <= background["x"] + background["width"] + 1
    assert label["width"] < background["width"] / 2
    assert label["height"] >= 40
    assert first_node["y"] >= label["y"] + label["height"] - 2
    assert label["z_index"] > 50


def test_layered_section_label_shortens_overlong_group_titles() -> None:
    plan = {
        "title": "企业级 AI 平台全景架构图",
        "layout": "layered",
        "palette": "business",
        "groups": [
            {"title": "权限与租户隔离层", "nodes": ["身份认证\nSSO 单点登录", "租户隔离\n数据与资源隔离"]},
            {"title": "Agent编排层【核心】", "nodes": ["工作流编排\n低代码流程配置", "工具集成\n第三方 API 调用"]},
        ],
        "edges": [],
    }

    shape_entries, _ = build_create_notes_payload(plan)
    labels = {entry["key"]: entry["node"]["text"]["text"] for entry in shape_entries if entry["key"].startswith("label")}

    assert labels["label0"] == "权限层"
    assert labels["label1"] == "编排层"


def test_title_and_caption_render_above_connectors() -> None:
    title = build_shape_node("企业级 AI 平台全景架构图", x=100, y=20, width=500, height=52, kind="title")
    caption = build_shape_node("接入层", x=120, y=80, width=220, height=28, kind="section")

    assert title["z_index"] > 50
    assert caption["z_index"] > 50


def test_fallback_plan_adjusts_information_density_by_prompt_detail() -> None:
    simple_plan = fallback_plan_from_message("帮我画一个简单架构图")
    normal_plan = fallback_plan_from_message("帮我画一个 AI 网关架构图")
    detailed_plan = fallback_plan_from_message("帮我画一个完整详细的 AI 网关架构图")

    assert len(simple_plan["groups"]) == 3
    assert len(normal_plan["groups"]) == 4
    assert len(detailed_plan["groups"]) == 5
    assert 2 <= len(simple_plan["groups"][0]["nodes"]) <= 3
    assert 3 <= len(normal_plan["groups"][0]["nodes"]) <= 4
    assert 4 <= len(detailed_plan["groups"][0]["nodes"]) <= 6


def test_fallback_plan_limits_group_size_and_edges_for_detailed_layered_plan() -> None:
    plan = fallback_plan_from_message("帮我画一个完整详细的 AI 网关架构图")

    for group in plan["groups"]:
        assert 2 <= len(group["nodes"]) <= 5

    assert len(plan["edges"]) <= 8


def test_palette_inference_only_switches_on_explicit_style_words() -> None:
    assert infer_palette_name("帮我画一个企业级技术架构图") == "classic"
    assert infer_palette_name("帮我画一个商务风架构图") == "business"
    assert infer_palette_name("帮我画一个科技风架构图") == "tech"
    assert infer_palette_name("帮我画一个学术风架构图") == "minimal"


def test_detailed_tree_plan_expands_to_second_level_children() -> None:
    plan = fallback_plan_from_message("请画一个完整详细的组织架构图")
    shape_entries, connector_entries = build_create_notes_payload(plan)

    assert plan["layout"] == "tree"
    assert plan["groups"][0]["child_groups"]
    assert any(entry["key"].startswith("bg") for entry in shape_entries)
    assert any(entry["key"].startswith("g2n") for entry in shape_entries)
    assert any(connector["source_key"].startswith("g1n") for connector in connector_entries)


def test_simple_tree_plan_still_contains_second_level_children() -> None:
    plan = fallback_plan_from_message("请画一个简单的组织架构图")

    assert plan["layout"] == "tree"
    assert plan["groups"][0]["child_groups"]


def test_normalize_tree_plan_keeps_original_plan_shape() -> None:
    plan = {
        "title": "组织架构图",
        "layout": "tree",
        "groups": [
            {
                "title": "组织结构",
                "root": "AI 产品研发负责人",
                "children": ["产品", "设计", "前端", "后端", "算法", "测试", "运营", "数据"],
            }
        ],
        "edges": [],
    }

    normalized = normalize_create_notes_plan(plan, "帮我画一个完整详细的 AI 产品研发组织架构图")
    group = normalized["groups"][0]

    assert group["children"] == ["产品", "设计", "前端", "后端", "算法", "测试", "运营", "数据"]


def test_normalize_plan_inferrs_layout_from_structure_before_message_keywords() -> None:
    plan = {
        "title": "",
        "layout": "",
        "groups": [
            {
                "title": "组织结构",
                "root": "研发负责人",
                "children": ["产品线", "技术线"],
            }
        ],
        "edges": [],
    }

    normalized = normalize_create_notes_plan(plan, "帮我画一个图")

    assert normalized["layout"] == "tree"
    assert normalized["palette"] == "classic"
    assert normalized["title"] == "图"


def test_normalize_matrix_groups_translates_llm_style_group_rows_into_columns_and_rows() -> None:
    plan = {
        "title": "企业级AI平台方案对比矩阵",
        "layout": "matrix",
        "groups": [
            {"title": "表头", "nodes": ["对比维度", "自建方案", "开源方案", "云厂商方案"]},
            {"title": "成本维度", "nodes": ["成本", "高", "中", "低"]},
            {"title": "可控性维度", "nodes": ["可控性", "高", "中", "低"]},
        ],
        "edges": [],
    }

    normalized = normalize_create_notes_plan(plan, "请画一个方案对比矩阵")

    assert normalized["layout"] == "matrix"
    assert len(normalized["groups"]) == 1
    assert normalized["groups"][0]["columns"] == ["对比维度", "自建方案", "开源方案", "云厂商方案"]
    assert normalized["groups"][0]["rows"] == [["成本", "高", "中", "低"], ["可控性", "高", "中", "低"]]


def test_island_plan_uses_representative_dashed_edges() -> None:
    plan = fallback_plan_from_message("做一个完整详细的微服务系统拓扑")
    shape_entries, connector_entries = build_create_notes_payload(plan)

    assert plan["layout"] == "island"
    assert len(plan["groups"]) == 4
    assert any(edge.get("dashed") for edge in plan["edges"])
    assert len([entry for entry in shape_entries if entry["key"].startswith("bg")]) == 4
    assert any(entry["key"].startswith("g3n") for entry in shape_entries)
    assert any(connector["source_key"].startswith("g2") for connector in connector_entries)


def test_island_background_wraps_estimated_node_sizes() -> None:
    plan = {
        "title": "系统集成图",
        "palette": "classic",
        "layout": "island",
        "groups": [
            {
                "title": "接入域",
                "nodes": ["统一入口\n外部系统接入", "权限控制\n令牌与会话校验", "观测中心\n日志与告警追踪"],
            }
        ],
        "edges": [],
    }

    shape_entries, _ = build_create_notes_payload(plan)
    background = next(entry["node"] for entry in shape_entries if entry["key"] == "bg0")

    assert background["width"] >= 300
    assert background["height"] >= 170


def test_free_plan_keeps_compact_problem_analysis_content() -> None:
    plan = fallback_plan_from_message("画一个完整详细的鱼骨图分析问题")

    assert plan["layout"] == "free"
    assert len(plan["groups"]) == 1
    assert 4 <= len(plan["groups"][0]["nodes"]) <= 5
    assert any(edge.get("dashed") for edge in plan["edges"])


def test_matrix_headers_use_accent_cells_instead_of_transparent_titles() -> None:
    plan = fallback_plan_from_message("帮我做一个完整详细的能力对比矩阵")
    shape_entries, _ = build_create_notes_payload(plan)
    header = next(entry["node"] for entry in shape_entries if entry["key"] == "g0h0")

    assert header["style"]["fill_opacity"] == 100
    assert header["style"]["border_style"] == "solid"
    assert header["style"]["fill_color"] == get_palette("classic")["accent"]["fill_color"]
    assert header["text"]["font_size"] == 15
    assert header["text"]["font_weight"] == "bold"


def test_matrix_payload_uses_safe_cell_heights_for_multiline_text() -> None:
    plan = {
        "title": "企业级AI平台方案对比矩阵",
        "layout": "matrix",
        "palette": "business",
        "groups": [
            {
                "title": "能力矩阵",
                "columns": ["维度", "自建方案\n自主研发", "开源方案\n二次开发", "云厂商方案\n采购服务"],
                "rows": [
                    ["成本\n总投入规模", "高\n硬件+人力+时间成本", "中\n授权+二次开发成本", "低\n按需付费无前置投入"],
                ],
            }
        ],
        "edges": [],
    }

    shape_entries, _ = build_create_notes_payload(plan)
    header = next(entry["node"] for entry in shape_entries if entry["key"] == "g0h1")
    body = next(entry["node"] for entry in shape_entries if entry["key"] == "g0n0_1")

    assert header["height"] >= 64
    assert body["height"] >= 64


def test_edge_selection_uses_representative_subset_for_dense_graph() -> None:
    plan = {
        "title": "Dense",
        "palette": "classic",
        "layout": "layered",
        "groups": [
            {"title": "G1", "nodes": ["A1", "A2", "A3"]},
            {"title": "G2", "nodes": ["B1", "B2", "B3"]},
            {"title": "G3", "nodes": ["C1", "C2", "C3"]},
        ],
        "edges": [
            {"from": f"g0n{i}", "to": f"g1n{j}", "direction": "tb"}
            for i in range(3)
            for j in range(3)
        ] + [
            {"from": f"g1n{i}", "to": f"g2n{j}", "direction": "tb"}
            for i in range(3)
            for j in range(3)
        ],
    }

    _, connector_entries = build_create_notes_payload(plan)

    assert len(plan["edges"]) == 18
    assert len(connector_entries) == 8


def test_edge_selection_keeps_more_representative_edges_for_medium_graph() -> None:
    plan = {
        "title": "Medium",
        "palette": "classic",
        "layout": "layered",
        "groups": [
            {"title": "G1", "nodes": ["A1", "A2", "A3"]},
            {"title": "G2", "nodes": ["B1", "B2", "B3"]},
            {"title": "G3", "nodes": ["C1", "C2", "C3"]},
        ],
        "edges": [
            {"from": "g0n0", "to": "g1n0", "direction": "tb"},
            {"from": "g0n0", "to": "g1n1", "direction": "tb"},
            {"from": "g0n1", "to": "g1n1", "direction": "tb"},
            {"from": "g0n1", "to": "g1n2", "direction": "tb"},
            {"from": "g0n2", "to": "g1n0", "direction": "tb"},
            {"from": "g0n2", "to": "g1n2", "direction": "tb"},
            {"from": "g1n0", "to": "g2n0", "direction": "tb"},
            {"from": "g1n0", "to": "g2n1", "direction": "tb"},
            {"from": "g1n1", "to": "g2n1", "direction": "tb"},
            {"from": "g1n1", "to": "g2n2", "direction": "tb"},
            {"from": "g1n2", "to": "g2n0", "direction": "tb"},
            {"from": "g1n2", "to": "g2n2", "direction": "tb"},
        ],
    }

    _, connector_entries = build_create_notes_payload(plan)

    assert len(plan["edges"]) == 12
    assert len(connector_entries) == 8


def test_tree_connectors_use_right_angled_polyline() -> None:
    plan = fallback_plan_from_message("请画一个完整详细的组织架构图")
    shape_entries, connector_entries = build_create_notes_payload(plan)
    key_to_node_id = {
        entry["key"]: f"node-{index}"
        for index, entry in enumerate(shape_entries)
        if entry["key"].startswith("g")
    }

    connectors = build_connectors_from_mapping(connector_entries, key_to_node_id)

    assert any(connector["connector"]["shape"] == "right_angled_polyline" for connector in connectors)


def test_tree_root_starts_below_title_band() -> None:
    plan = fallback_plan_from_message("请画一个完整详细的组织架构图")
    shape_entries, _ = build_create_notes_payload(plan)
    title = next(entry["node"] for entry in shape_entries if entry["key"] == "title")
    root = next(entry["node"] for entry in shape_entries if entry["key"] == "g0n0")

    assert root["y"] >= title["y"] + title["height"] + 30


def test_tree_root_uses_independent_neutral_border() -> None:
    plan = fallback_plan_from_message("请画一个完整详细的组织架构图")
    shape_entries, _ = build_create_notes_payload(plan)
    root = next(entry["node"] for entry in shape_entries if entry["key"] == "g0n0")

    assert root["style"]["fill_color"] == "#FFFFFF"
    assert root["style"]["border_color"] == "#DEE0E3"


def test_title_node_uses_taller_safe_box_for_chinese_bold_text() -> None:
    plan = fallback_plan_from_message("帮我画一个完整详细的 AI 产品研发组织架构图")
    shape_entries, _ = build_create_notes_payload(plan)
    title = next(entry["node"] for entry in shape_entries if entry["key"] == "title")

    assert title["height"] == 60




def test_connector_mapping_builds_real_connector_nodes() -> None:
    plan = fallback_plan_from_message("帮我画一个 AI 网关架构图")
    shape_entries, connector_entries = build_create_notes_payload(plan)
    key_to_node_id = {
        entry["key"]: f"node-{index}"
        for index, entry in enumerate(shape_entries)
        if entry["key"].startswith("g")
    }

    connectors = build_connectors_from_mapping(connector_entries, key_to_node_id)

    assert connectors
    assert connectors[0]["type"] == "connector"
    assert connectors[0]["connector"]["start"]["attached_object"]["id"].startswith("node-")


def test_parse_create_notes_plan_accepts_compact_json_dict() -> None:
    parsed = parse_create_notes_plan(
        '{"title":"测试图","layout":"layered","groups":[{"title":"接入层","nodes":["A","B"]}],"edges":[]}'
    )

    assert parsed is not None
    assert parsed["title"] == "测试图"


def test_fallback_title_removes_detail_prompt_words() -> None:
    plan = fallback_plan_from_message("帮我画一个完整详细的 AI 产品研发组织架构图，需要包含产品、设计、前端")

    assert plan["title"] == "AI 产品研发组织架构图"
