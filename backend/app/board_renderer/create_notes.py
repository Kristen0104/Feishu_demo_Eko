from __future__ import annotations

import json
import re
from typing import Any


LAYOUT_LAYERED = "layered"
LAYOUT_MATRIX = "matrix"
LAYOUT_ISLAND = "island"
LAYOUT_TREE = "tree"
LAYOUT_FREE = "free"

LAYOUT_MODES = (
    LAYOUT_LAYERED,
    LAYOUT_MATRIX,
    LAYOUT_ISLAND,
    LAYOUT_TREE,
    LAYOUT_FREE,
)

BOARD_RENDERER_PALETTES: dict[str, dict[str, Any]] = {
    "classic": {
        "name": "classic",
        "groups": (
            {"fill_color": "#F0F4FC", "border_color": "#5178C6"},
            {"fill_color": "#EAE2FE", "border_color": "#8569CB"},
            {"fill_color": "#DFF5E5", "border_color": "#509863"},
            {"fill_color": "#FEF1CE", "border_color": "#D4B45B"},
            {"fill_color": "#FEE3E2", "border_color": "#D25D5A"},
        ),
        "node": {"fill_color": "#FFFFFF", "border_color": "#5178C6"},
        "accent": {"fill_color": "#1F2329", "border_color": "#1F2329", "font_color": "#FFFFFF"},
        "line_color": "#BBBFC4",
        "text_color": "#1F2329",
    },
    "business": {
        "name": "business",
        "groups": (
            {"fill_color": "#EDF2F7", "border_color": "#4A6FA5"},
            {"fill_color": "#D4E0ED", "border_color": "#4A6FA5"},
            {"fill_color": "#E8EDF3", "border_color": "#5A7B9A"},
            {"fill_color": "#F0F0F0", "border_color": "#8895A7"},
            {"fill_color": "#F8F9FA", "border_color": "#ADB5BD"},
        ),
        "node": {"fill_color": "#FFFFFF", "border_color": "#718BAE"},
        "accent": {"fill_color": "#2D4A7A", "border_color": "#2D4A7A", "font_color": "#FFFFFF"},
        "line_color": "#718BAE",
        "text_color": "#1A202C",
    },
    "tech": {
        "name": "tech",
        "groups": (
            {"fill_color": "#0F172A", "border_color": "#1E293B"},
            {"fill_color": "#1E293B", "border_color": "#3B82F6"},
            {"fill_color": "#1E293B", "border_color": "#8B5CF6"},
            {"fill_color": "#1E293B", "border_color": "#10B981"},
            {"fill_color": "#1E293B", "border_color": "#334155"},
        ),
        "node": {"fill_color": "#1E293B", "border_color": "#334155"},
        "accent": {"fill_color": "#2563EB", "border_color": "#3B82F6", "font_color": "#FFFFFF"},
        "line_color": "#475569",
        "text_color": "#E2E8F0",
    },
    "fresh": {
        "name": "fresh",
        "groups": (
            {"fill_color": "#F0FDF4", "border_color": "#86EFAC"},
            {"fill_color": "#DCFCE7", "border_color": "#4ADE80"},
            {"fill_color": "#ECFDF5", "border_color": "#6EE7B7"},
            {"fill_color": "#F0FDFA", "border_color": "#5EEAD4"},
            {"fill_color": "#F8FAFC", "border_color": "#94A3B8"},
        ),
        "node": {"fill_color": "#FFFFFF", "border_color": "#86EFAC"},
        "accent": {"fill_color": "#16A34A", "border_color": "#16A34A", "font_color": "#FFFFFF"},
        "line_color": "#86EFAC",
        "text_color": "#14532D",
    },
    "minimal": {
        "name": "minimal",
        "groups": (
            {"fill_color": "#F8F9FA", "border_color": "#DEE2E6"},
            {"fill_color": "#E9ECEF", "border_color": "#ADB5BD"},
            {"fill_color": "#F1F3F5", "border_color": "#868E96"},
            {"fill_color": "#F8F9FA", "border_color": "#ADB5BD"},
            {"fill_color": "#FFFFFF", "border_color": "#CED4DA"},
        ),
        "node": {"fill_color": "#FFFFFF", "border_color": "#CED4DA"},
        "accent": {"fill_color": "#495057", "border_color": "#495057", "font_color": "#FFFFFF"},
        "line_color": "#ADB5BD",
        "text_color": "#212529",
    },
}

BOARD_RENDERER_LAYOUT_RULES: dict[str, Any] = {
    "layered": {
        "label": "分层条带",
        "keywords": ("架构", "技术栈", "流程图", "层级", "分层", "用户层", "服务层", "数据层"),
        "description": "有明确上下层级时优先使用，默认最安全。",
    },
    "matrix": {
        "label": "行列对齐",
        "keywords": ("矩阵", "对比表", "功能矩阵", "卡片墙", "看板", "表格"),
        "description": "对比、评估、表格类内容使用网格排布。",
    },
    "island": {
        "label": "岛屿式",
        "keywords": ("微服务", "系统集成", "平级互联", "独立模块", "拓扑"),
        "description": "多个独立模块平级互联时使用。",
    },
    "tree": {
        "label": "树状展开",
        "keywords": ("组织架构", "组织图", "依赖树", "模块依赖", "树形"),
        "description": "根节点向下展开的层级树。",
    },
    "free": {
        "label": "自由定位",
        "keywords": ("鱼骨图", "地图", "飞轮", "柱状图", "折线图", "自由拓扑"),
        "description": "坐标/方位本身有语义时使用。",
    },
}

BOARD_RENDERER_CONNECTOR_RULES: dict[str, Any] = {
    "default_shape": "polyline",
    "default_start_arrow": "none",
    "default_end_arrow": "triangle_arrow",
    "default_style": "solid",
    "default_width": "narrow",
    "default_z_index": 50,
    "direction_map": {
        "lr": {"start": ("right", {"x": 1, "y": 0.5}, "y"), "end": ("left", {"x": 0, "y": 0.5}, "y")},
        "tb": {"start": ("bottom", {"x": 0.5, "y": 1}, "x"), "end": ("top", {"x": 0.5, "y": 0}, "x")},
        "rl": {"start": ("left", {"x": 0, "y": 0.5}, "y"), "end": ("right", {"x": 1, "y": 0.5}, "y")},
        "bt": {"start": ("top", {"x": 0.5, "y": 0}, "x"), "end": ("bottom", {"x": 0.5, "y": 1}, "x")},
    },
}

BOARD_RENDERER_TYPOGRAPHY_RULES: dict[str, Any] = {
    "title": {"font_size": 24, "font_weight": "bold", "horizontal_align": "center", "vertical_align": "mid"},
    "section": {"font_size": 18, "font_weight": "bold", "horizontal_align": "left", "vertical_align": "mid"},
    "accent": {"font_size": 15, "font_weight": "bold", "horizontal_align": "center", "vertical_align": "mid"},
    "body": {"font_size": 14, "font_weight": "regular", "horizontal_align": "center", "vertical_align": "mid"},
    "node": {"font_size": 14, "font_weight": "regular", "horizontal_align": "center", "vertical_align": "mid"},
    "caption": {"font_size": 13, "font_weight": "regular", "horizontal_align": "left", "vertical_align": "mid"},
}

BOARD_RENDERER_SCHEMA_RULES: dict[str, Any] = {
    "shape_node_fields": ("type", "x", "y", "width", "height", "z_index", "composite_shape", "text", "style"),
    "connector_fields": ("type", "width", "height", "z_index", "connector", "style"),
    "shape_type_fields": ("type",),
    "text_fields": ("text", "font_size", "font_weight", "horizontal_align", "vertical_align"),
    "style_fields": ("fill_color", "fill_opacity", "border_style", "border_color", "border_width", "border_opacity"),
    "connector_style_fields": ("border_color", "border_opacity", "border_style", "border_width"),
}

CREATE_NOTES_RULE_SUMMARY = "\n".join(
    [
        "Follow the feishu-cli create-notes route exactly.",
        "Choose layout by information structure first: matrix, tree, island, free, then layered as the default.",
        "Use absolute coordinates and the safe schema fields only.",
        "Use the selected palette consistently: background bands are light, content nodes follow the palette, connectors stay gray.",
        "Estimate node size from text length and line count, align long or multi-line text to the left, and keep node text short.",
        "Create shapes before connectors.",
    ]
)

MATRIX_KEYWORDS = tuple(BOARD_RENDERER_LAYOUT_RULES["matrix"]["keywords"])
TREE_KEYWORDS = tuple(BOARD_RENDERER_LAYOUT_RULES["tree"]["keywords"])
ISLAND_KEYWORDS = tuple(BOARD_RENDERER_LAYOUT_RULES["island"]["keywords"])
FREE_KEYWORDS = tuple(BOARD_RENDERER_LAYOUT_RULES["free"]["keywords"])
LAYERED_KEYWORDS = tuple(BOARD_RENDERER_LAYOUT_RULES["layered"]["keywords"])
SHORT_TEXT_MAX_LEN = 15
TEXT_LINE_HEIGHT = 22
TEXT_VERTICAL_PADDING = 20
NODE_SINGLE_LINE_SAFE_HEIGHT = 44
NODE_DOUBLE_LINE_SAFE_HEIGHT = 64
NODE_MULTI_LINE_SAFE_HEIGHT = 80
TITLE_SAFE_HEIGHT = 60
SECTION_SAFE_HEIGHT = 40


def get_palette(name: str = "classic") -> dict[str, Any]:
    palette = BOARD_RENDERER_PALETTES.get(name.lower())
    if palette is None:
        return BOARD_RENDERER_PALETTES["classic"]
    return palette


def choose_layout_mode(message: str) -> str:
    normalized = _normalize_text(message)
    if any(keyword in normalized for keyword in ("组织架构", "组织图", "汇报关系", "部门", "团队")):
        return LAYOUT_TREE
    if any(keyword in normalized for keyword in ("矩阵", "对比", "表格", "维度")):
        return LAYOUT_MATRIX
    if any(keyword in normalized for keyword in ("微服务", "拓扑", "集成", "平级互联", "独立模块")):
        return LAYOUT_ISLAND
    if any(keyword in normalized for keyword in ("鱼骨图", "地图", "飞轮", "柱状图", "折线图", "自由拓扑")):
        return LAYOUT_FREE
    return LAYOUT_LAYERED


def estimate_node_size(text: str) -> tuple[int, int]:
    lines = _split_lines(text)
    visible_len = max((len(line) for line in lines), default=0)
    if len(lines) >= 3 or visible_len > 18:
        width = min(240, max(200, visible_len * 14 + 24))
        height = max(NODE_MULTI_LINE_SAFE_HEIGHT, TEXT_LINE_HEIGHT * len(lines) + TEXT_VERTICAL_PADDING)
        return width, height
    if len(lines) == 2:
        width = min(220, max(180, visible_len * 14 + 24))
        return width, NODE_DOUBLE_LINE_SAFE_HEIGHT
    if visible_len <= 4:
        return 120, NODE_SINGLE_LINE_SAFE_HEIGHT
    if visible_len <= 8:
        return 160, NODE_SINGLE_LINE_SAFE_HEIGHT
    if visible_len <= 15:
        return 180, NODE_DOUBLE_LINE_SAFE_HEIGHT
    return 200, NODE_MULTI_LINE_SAFE_HEIGHT


def choose_text_alignment(text: str, *, kind: str = "node") -> tuple[str, str]:
    lines = _split_lines(text)
    visible_len = max((len(line) for line in lines), default=0)

    if kind in {"title", "heading", "accent"}:
        return "center", "mid"
    if kind in {"background", "caption", "section"}:
        return "left", "top"
    if len(lines) > 1:
        return "left", "top"
    if visible_len > SHORT_TEXT_MAX_LEN:
        return "left", "mid"
    return "center", "mid"


def estimate_text_layout(text: str, *, kind: str = "node") -> dict[str, Any]:
    width, height = estimate_node_size(text)
    horizontal_align, vertical_align = choose_text_alignment(text, kind=kind)
    typography = BOARD_RENDERER_TYPOGRAPHY_RULES.get(kind, BOARD_RENDERER_TYPOGRAPHY_RULES["node"])
    return {
        "width": width,
        "height": height,
        "font_size": typography["font_size"],
        "font_weight": typography["font_weight"],
        "horizontal_align": horizontal_align,
        "vertical_align": vertical_align,
    }


def build_shape_node(
    text: str,
    *,
    x: int,
    y: int,
    width: int | None = None,
    height: int | None = None,
    palette: str = "classic",
    group_index: int = 0,
    kind: str = "node",
    shape_type: str = "round_rect",
) -> dict[str, Any]:
    palette_data = get_palette(palette)
    group = palette_data["groups"][group_index % len(palette_data["groups"])]
    node_palette = palette_data["node"]
    size_width = width
    size_height = height
    if size_width is None or size_height is None:
        estimated_width, estimated_height = estimate_node_size(text)
        size_width = estimated_width if size_width is None else size_width
        size_height = estimated_height if size_height is None else size_height
    text_layout = estimate_text_layout(text, kind=kind)

    node: dict[str, Any] = {
        "type": "composite_shape",
        "x": x,
        "y": y,
        "width": size_width,
        "height": size_height,
        "z_index": 10,
        "composite_shape": {"type": shape_type},
        "text": {
            "text": text,
            "font_size": text_layout["font_size"],
            "font_weight": text_layout["font_weight"],
            "horizontal_align": text_layout["horizontal_align"],
            "vertical_align": text_layout["vertical_align"],
        },
        "style": {
            "fill_color": node_palette["fill_color"],
            "fill_opacity": 100,
            "border_style": "solid",
            "border_color": group["border_color"],
            "border_width": "medium",
            "border_opacity": 100,
        },
    }

    if kind == "background":
        node["z_index"] = 0
        node["text"] = {"text": ""}
        node["style"] = {
            "fill_color": group["fill_color"],
            "fill_opacity": 25,
            "border_style": "solid",
            "border_color": group["border_color"],
            "border_width": "narrow",
            "border_opacity": 40,
        }
    elif kind == "section":
        node["z_index"] = 60
        node["text"] = {
            "text": text,
            "font_size": BOARD_RENDERER_TYPOGRAPHY_RULES["section"]["font_size"],
            "font_weight": BOARD_RENDERER_TYPOGRAPHY_RULES["section"]["font_weight"],
            "horizontal_align": "left",
            "vertical_align": "mid",
        }
        node["style"] = {"fill_opacity": 0, "border_style": "none"}
    elif kind == "independent":
        node["style"] = {
            "fill_color": "#FFFFFF",
            "fill_opacity": 100,
            "border_style": "solid",
            "border_color": "#DEE0E3",
            "border_width": "medium",
            "border_opacity": 100,
        }
    elif kind == "title":
        node["z_index"] = 60
        node["text"] = {
            "text": text,
            "font_size": BOARD_RENDERER_TYPOGRAPHY_RULES["title"]["font_size"],
            "font_weight": BOARD_RENDERER_TYPOGRAPHY_RULES["title"]["font_weight"],
            "horizontal_align": BOARD_RENDERER_TYPOGRAPHY_RULES["title"]["horizontal_align"],
            "vertical_align": BOARD_RENDERER_TYPOGRAPHY_RULES["title"]["vertical_align"],
        }
        node["style"] = {"fill_opacity": 0, "border_style": "none"}
    elif kind == "accent":
        node["style"] = {
            "fill_color": palette_data["accent"]["fill_color"],
            "fill_opacity": 100,
            "border_style": "solid",
            "border_color": palette_data["accent"]["border_color"],
            "border_width": "medium",
            "border_opacity": 100,
        }
    elif kind == "caption":
        node["z_index"] = 60
        node["text"] = {
            "text": text,
            "font_size": BOARD_RENDERER_TYPOGRAPHY_RULES["caption"]["font_size"],
            "font_weight": BOARD_RENDERER_TYPOGRAPHY_RULES["caption"]["font_weight"],
            "horizontal_align": BOARD_RENDERER_TYPOGRAPHY_RULES["caption"]["horizontal_align"],
            "vertical_align": "top",
        }
        node["style"] = {"fill_opacity": 0, "border_style": "none"}

    return node


def build_background_region(
    text: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    palette: str = "classic",
    group_index: int = 0,
) -> dict[str, Any]:
    return build_shape_node(
        text,
        x=x,
        y=y,
        width=width,
        height=height,
        palette=palette,
        group_index=group_index,
        kind="background",
    )


def build_title_node(text: str, *, x: int, y: int, width: int, height: int = TITLE_SAFE_HEIGHT) -> dict[str, Any]:
    return build_shape_node(text, x=x, y=y, width=width, height=height, kind="title")


def build_section_label(text: str, *, x: int, y: int, width: int | None = None, height: int = SECTION_SAFE_HEIGHT) -> dict[str, Any]:
    if width is None:
        estimated = estimate_text_layout(text, kind="section")
        width = max(120, min(240, int(estimated["width"])))
    return build_shape_node(text, x=x, y=y, width=width, height=height, kind="section")


def build_connector(
    source_id: str,
    target_id: str,
    *,
    direction: str = "lr",
    palette: str = "classic",
    source_slot: int = 0,
    source_total: int = 1,
    target_slot: int = 0,
    target_total: int = 1,
    shape: str | None = None,
    dashed: bool = False,
) -> dict[str, Any]:
    palette_data = get_palette(palette)
    direction_key = direction.lower()
    if direction_key not in BOARD_RENDERER_CONNECTOR_RULES["direction_map"]:
        raise ValueError(f"Unsupported connector direction: {direction}")

    direction_rule = BOARD_RENDERER_CONNECTOR_RULES["direction_map"][direction_key]
    start_snap, start_position, start_axis = direction_rule["start"]
    end_snap, end_position, end_axis = direction_rule["end"]

    return {
        "type": "connector",
        "width": 1,
        "height": 1,
        "z_index": BOARD_RENDERER_CONNECTOR_RULES["default_z_index"],
        "connector": {
            "shape": shape or BOARD_RENDERER_CONNECTOR_RULES["default_shape"],
            "start": {
                "arrow_style": BOARD_RENDERER_CONNECTOR_RULES["default_start_arrow"],
                "attached_object": {
                    "id": source_id,
                    "position": _fanout_position(start_position, source_slot, source_total, axis=start_axis),
                    "snap_to": start_snap,
                },
            },
            "end": {
                "arrow_style": BOARD_RENDERER_CONNECTOR_RULES["default_end_arrow"],
                "attached_object": {
                    "id": target_id,
                    "position": _fanout_position(end_position, target_slot, target_total, axis=end_axis),
                    "snap_to": end_snap,
                },
            },
        },
        "style": {
            "border_color": palette_data["line_color"],
            "border_opacity": 100,
            "border_style": "dash" if dashed else BOARD_RENDERER_CONNECTOR_RULES["default_style"],
            "border_width": BOARD_RENDERER_CONNECTOR_RULES["default_width"],
        },
    }


def build_layered_row_positions(
    count: int,
    *,
    canvas_width: int = 800,
    node_width: int = 160,
    gap: int = 60,
    y: int = 80,
) -> list[tuple[int, int]]:
    if count <= 0:
        return []
    total_width = count * node_width + max(0, count - 1) * gap
    start_x = int(round((canvas_width - total_width) / 2))
    return [(start_x + index * (node_width + gap), y) for index in range(count)]


def build_variable_row_positions(
    widths: list[int],
    *,
    canvas_width: int,
    gap: int = 60,
    y: int,
) -> list[tuple[int, int]]:
    if not widths:
        return []
    total_width = sum(widths) + max(0, len(widths) - 1) * gap
    start_x = int(round((canvas_width - total_width) / 2))
    positions: list[tuple[int, int]] = []
    current_x = start_x
    for width in widths:
        positions.append((current_x, y))
        current_x += width + gap
    return positions


def build_matrix_positions(
    rows: int,
    cols: int,
    *,
    start_x: int = 100,
    start_y: int = 80,
    cell_width: int = 150,
    cell_height: int = 40,
    col_gap: int = 20,
    row_gap: int = 15,
) -> list[list[tuple[int, int]]]:
    return [
        [
            (start_x + col * (cell_width + col_gap), start_y + row * (cell_height + row_gap))
            for col in range(cols)
        ]
        for row in range(rows)
    ]


def build_tree_child_positions(
    parent_x: int,
    parent_width: int,
    count: int,
    *,
    child_width: int = 160,
    sibling_gap: int = 80,
    child_y: int = 170,
) -> list[tuple[int, int]]:
    if count <= 0:
        return []
    total_width = count * child_width + max(0, count - 1) * sibling_gap
    parent_center_x = parent_x + parent_width / 2
    start_x = int(round(parent_center_x - total_width / 2))
    return [(start_x + index * (child_width + sibling_gap), child_y) for index in range(count)]


def recenter_shape_entries(
    shape_entries: list[dict[str, Any]],
    *,
    min_canvas_width: int = 800,
) -> list[dict[str, Any]]:
    content_entries = [
        entry for entry in shape_entries
        if isinstance(entry, dict)
        and entry.get("key") != "title"
        and isinstance(entry.get("node"), dict)
        and isinstance(entry["node"].get("x"), int)
        and isinstance(entry["node"].get("y"), int)
        and isinstance(entry["node"].get("width"), int)
        and isinstance(entry["node"].get("height"), int)
    ]
    if not content_entries:
        return shape_entries

    min_x = min(entry["node"]["x"] for entry in content_entries)
    max_x = max(entry["node"]["x"] + entry["node"]["width"] for entry in content_entries)
    content_width = max_x - min_x
    canvas_width = max(min_canvas_width, content_width + 120)
    offset = int(round((canvas_width - content_width) / 2 - min_x))

    centered: list[dict[str, Any]] = []
    for entry in shape_entries:
        node = entry.get("node")
        if not isinstance(node, dict):
            centered.append(entry)
            continue
        updated_entry = dict(entry)
        updated_node = dict(node)
        if entry.get("key") == "title":
            title_width = max(300, min(1200, content_width))
            updated_node["x"] = int(round((canvas_width - title_width) / 2))
            updated_node["width"] = title_width
        else:
            updated_node["x"] = int(updated_node["x"]) + offset
        updated_entry["node"] = updated_node
        centered.append(updated_entry)
    return centered


def _normalize_text(value: str) -> str:
    return value.replace("\u3000", " ").replace("\n", " ").lower()


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in value for keyword in keywords)


def _split_lines(value: str) -> list[str]:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return lines or [""]


def _shorten_layered_section_title(value: str) -> str:
    title = re.sub(r"[（(【\[].*?[）)】\]]", "", value).strip()
    title = re.sub(r"\s+", "", title)
    if not title:
        return "分层"

    mapping = (
        (("接入", "入口", "渠道", "终端"), "接入层"),
        (("权限", "租户", "鉴权", "认证", "隔离"), "权限层"),
        (("agent", "编排", "workflow", "工作流", "调度", "协作", "prompt"), "编排层"),
        (("模型", "检索", "rag", "向量", "embedding"), "模型层"),
        (("数据", "存储", "数据库", "对象存储", "缓存"), "数据层"),
        (("观测", "评测", "监控", "分析", "审计", "统计"), "观测层"),
    )
    normalized = _normalize_text(title)
    for keywords, short_title in mapping:
        if any(keyword in normalized for keyword in keywords):
            return short_title

    if len(title) <= 8:
        return title

    if "层" in title:
        prefix = title.split("层", 1)[0]
        if len(prefix) <= 4:
            return f"{prefix}层"
    return title[:6]


def _fanout_position(
    base_position: dict[str, float],
    slot: int,
    total: int,
    *,
    axis: str,
) -> dict[str, float]:
    if total <= 1:
        return dict(base_position)
    ratio = (slot + 1) / (total + 1)
    if axis == "x":
        return {"x": round(ratio, 3), "y": base_position["y"]}
    return {"x": base_position["x"], "y": round(ratio, 3)}


def parse_create_notes_plan(payload: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    if not isinstance(parsed.get("groups"), list):
        return None
    return parsed


def normalize_create_notes_plan(plan: dict[str, Any], message: str) -> dict[str, Any]:
    normalized = dict(plan)
    groups = normalized.get("groups") if isinstance(normalized.get("groups"), list) else []
    layout = str(normalized.get("layout") or "").strip().lower()
    if layout not in LAYOUT_MODES:
        normalized["layout"] = _infer_layout_mode_from_groups(groups, message)
    elif layout == LAYOUT_MATRIX:
        normalized["groups"] = _normalize_matrix_groups(groups)
    if not isinstance(normalized.get("palette"), str) or not normalized.get("palette"):
        normalized["palette"] = infer_palette_name(message)
    if not isinstance(normalized.get("title"), str) or not str(normalized.get("title")).strip():
        normalized["title"] = _infer_title(message)
    return normalized


def _infer_layout_mode_from_groups(groups: list[dict[str, Any]], message: str) -> str:
    if not groups or not isinstance(groups[0], dict):
        return choose_layout_mode(message)
    first_group = groups[0]
    if isinstance(first_group.get("columns"), list) and isinstance(first_group.get("rows"), list):
        return LAYOUT_MATRIX
    if first_group.get("root") and isinstance(first_group.get("children"), list):
        return LAYOUT_TREE
    if len(groups) > 1:
        return LAYOUT_ISLAND
    return choose_layout_mode(message)


def _normalize_matrix_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not groups:
        return groups
    first = groups[0] if isinstance(groups[0], dict) else {}
    if isinstance(first.get("columns"), list) and isinstance(first.get("rows"), list):
        return groups

    node_rows: list[list[str]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        nodes = _string_list(group.get("nodes"))
        if not nodes:
            continue
        node_rows.append(nodes)
    if len(node_rows) < 2:
        return groups

    column_count = len(node_rows[0])
    if column_count < 2:
        return groups
    if any(len(row) != column_count for row in node_rows):
        return groups

    return [
        {
            "title": str(first.get("title") or "能力矩阵"),
            "columns": node_rows[0],
            "rows": node_rows[1:],
        }
    ]


def infer_palette_name(message: str) -> str:
    normalized = _normalize_text(message)
    if any(keyword in normalized for keyword in ("经典", "classic")):
        return "classic"
    if any(keyword in normalized for keyword in ("商务风", "商务", "正式", "汇报风", "老板看")):
        return "business"
    if any(keyword in normalized for keyword in ("科技风", "tech", "暗色", "深色")):
        return "tech"
    if any(keyword in normalized for keyword in ("清新", "自然风", "fresh")):
        return "fresh"
    if any(keyword in normalized for keyword in ("极简", "极简风", "学术风", "论文风", "黑白")):
        return "minimal"
    return "classic"

def fallback_plan_from_message(message: str) -> dict[str, Any]:
    layout_mode = choose_layout_mode(message)
    title = _infer_title(message)
    detail_level = _infer_detail_level(message)

    if layout_mode == LAYOUT_MATRIX:
        rows = [
            ["性能", "高", "中"],
            ["成本", "中", "低"],
            ["稳定性", "高", "中"],
            ["扩展性", "高", "高"],
        ]
        if detail_level != "simple":
            rows.append(["运维性", "中", "高"])
        if detail_level == "detailed":
            rows.append(["安全性", "高", "中"])
        return {
            "title": title,
            "palette": infer_palette_name(message),
            "layout": LAYOUT_MATRIX,
            "groups": [
                {
                    "title": "能力矩阵",
                    "columns": ["维度", "方案 A", "方案 B"],
                    "rows": rows,
                }
            ],
            "edges": [],
        }
    if layout_mode == LAYOUT_TREE:
        children = ["产品设计线\n需求与体验", "技术研发线\n开发与交付"]
        child_groups: list[dict[str, Any]] = [
            {"parent": "产品设计线\n需求与体验", "children": ["产品团队\n需求拆解", "设计团队\n体验设计"]},
            {"parent": "技术研发线\n开发与交付", "children": ["后端团队\n服务开发", "前端团队\n界面实现"]},
        ]
        if detail_level != "simple":
            children.append("业务增长线\n运营与服务")
            child_groups.append({"parent": "业务增长线\n运营与服务", "children": ["运营团队\n增长活动", "客户成功\n用户服务"]})
        if detail_level == "detailed":
            children.append("数据算法线\n分析与智能")
            child_groups.append({"parent": "数据算法线\n分析与智能", "children": ["算法团队\n模型训练", "数据团队\n指标分析"]})
        edges = [{"from": "g0n0", "to": f"g1n{index}", "direction": "tb"} for index in range(len(children))]
        for parent_index, child_group in enumerate(child_groups):
            grand_children = _string_list(child_group.get("children"))[:2]
            for child_index in range(len(grand_children)):
                edges.append(
                    {
                        "from": f"g1n{children.index(str(child_group.get('parent') or ''))}",
                        "to": f"g2n{parent_index}_{child_index}",
                        "direction": "tb",
                        "shape": "right_angled_polyline",
                    }
                )
        return {
            "title": title,
            "palette": infer_palette_name(message),
            "layout": LAYOUT_TREE,
            "groups": [
                {
                    "title": "组织结构",
                    "root": "总部\n战略协调",
                    "children": children,
                    "child_groups": child_groups,
                }
            ],
            "edges": edges,
        }
    if layout_mode == LAYOUT_ISLAND:
        groups = [
            {"title": "接入域", "nodes": ["API 网关\n统一入口", "鉴权服务\n令牌校验"]},
            {"title": "业务域", "nodes": ["编排服务\n流程控制", "任务服务\n执行调度"]},
            {"title": "数据域", "nodes": ["向量库\n检索召回", "对象存储\n资料归档"]},
        ]
        if detail_level != "simple":
            groups[1]["nodes"].append("工作流引擎\n步骤编排")
        if detail_level == "detailed":
            groups.insert(2, {"title": "模型域", "nodes": ["模型路由\n模型分发", "重排服务\n结果排序"]})
            groups = _merge_small_groups(groups)
        edges = [
            {"from": "g0n0", "to": "g1n0", "direction": "lr"},
            {"from": "g0n1", "to": "g1n1", "direction": "lr", "dashed": True},
            {"from": "g1n0", "to": "g2n0", "direction": "tb"},
            {"from": "g1n1", "to": "g2n1", "direction": "tb", "dashed": True},
        ]
        if detail_level == "detailed":
            edges = [
                {"from": "g0n0", "to": "g1n0", "direction": "lr"},
                {"from": "g0n1", "to": "g1n1", "direction": "lr", "dashed": True},
                {"from": "g1n0", "to": "g2n0", "direction": "tb"},
                {"from": "g1n1", "to": "g2n1", "direction": "tb", "dashed": True},
                {"from": "g2n0", "to": "g3n0", "direction": "tb"},
                {"from": "g2n1", "to": "g3n1", "direction": "tb", "dashed": True},
            ]
        return {
            "title": title,
            "palette": infer_palette_name(message),
            "layout": LAYOUT_ISLAND,
            "groups": groups,
            "edges": edges,
        }
    if layout_mode == LAYOUT_FREE:
        free_nodes = ["核心问题\n待分析事项", "原因一\n流程阻塞", "原因二\n资源不足", "原因三\n协作偏差"]
        if detail_level != "simple":
            free_nodes[1] = "原因一\n链路阻塞"
            free_nodes[2] = "原因二\n资源排队"
        if detail_level == "detailed":
            free_nodes.append("原因四\n数据延迟")
        return {
            "title": title,
            "palette": infer_palette_name(message),
            "layout": LAYOUT_FREE,
            "groups": [
                {"title": "问题", "nodes": free_nodes},
            ],
            "edges": [
                {"from": "g0n1", "to": "g0n0", "direction": "lr"},
                {"from": "g0n2", "to": "g0n0", "direction": "lr", "dashed": True},
                {"from": "g0n3", "to": "g0n0", "direction": "rl"},
                *([{"from": "g0n4", "to": "g0n0", "direction": "tb", "dashed": True}] if detail_level == "detailed" else []),
            ],
        }
    layered_groups = _layered_groups_for_detail(detail_level)
    return {
        "title": title,
        "palette": infer_palette_name(message),
        "layout": LAYOUT_LAYERED,
        "groups": layered_groups,
        "edges": _build_layered_edges(layered_groups),
    }


def build_create_notes_payload(
    plan: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    layout_mode = str(plan.get("layout") or LAYOUT_LAYERED)
    palette = str(plan.get("palette") or "classic")
    title = str(plan.get("title") or "Feishu Board")
    groups = plan.get("groups") if isinstance(plan.get("groups"), list) else []
    edges = plan.get("edges") if isinstance(plan.get("edges"), list) else []

    shape_entries: list[dict[str, Any]] = []
    connector_entries: list[dict[str, Any]] = []
    shape_entries.append(
        {
            "key": "title",
            "node": build_title_node(title, x=150, y=20, width=500),
        }
    )

    if layout_mode == LAYOUT_MATRIX:
        shape_entries.extend(_build_matrix_payload(groups, palette))
    elif layout_mode == LAYOUT_TREE:
        shape_entries.extend(_build_tree_payload(groups, palette))
    elif layout_mode == LAYOUT_ISLAND:
        shape_entries.extend(_build_island_payload(groups, palette))
    elif layout_mode == LAYOUT_FREE:
        shape_entries.extend(_build_free_payload(groups, palette))
    else:
        shape_entries.extend(_build_layered_payload(groups, palette))

    shape_entries = recenter_shape_entries(shape_entries)

    group_node_keys = [entry["key"] for entry in shape_entries if entry["key"].startswith("g")]
    clipped_edges = _select_representative_edges(edges)
    for edge in clipped_edges:
        if not isinstance(edge, dict):
            continue
        source_key = str(edge.get("from") or "")
        target_key = str(edge.get("to") or "")
        if source_key not in group_node_keys or target_key not in group_node_keys:
            continue
        connector_entries.append(
            {
                "source_key": source_key,
                "target_key": target_key,
                "direction": str(edge.get("direction") or "lr"),
                "shape": edge.get("shape"),
                "dashed": bool(edge.get("dashed", False)),
            }
        )

    return shape_entries, connector_entries


def build_connectors_from_mapping(
    connector_entries: list[dict[str, Any]],
    key_to_node_id: dict[str, str],
    *,
    palette: str = "classic",
) -> list[dict[str, Any]]:
    source_groups: dict[str, list[dict[str, Any]]] = {}
    target_groups: dict[str, list[dict[str, Any]]] = {}
    for connector in connector_entries:
        source_groups.setdefault(connector["source_key"], []).append(connector)
        target_groups.setdefault(connector["target_key"], []).append(connector)

    built: list[dict[str, Any]] = []
    for connector in connector_entries:
        source_key = connector["source_key"]
        target_key = connector["target_key"]
        if source_key not in key_to_node_id or target_key not in key_to_node_id:
            continue
        built.append(
            build_connector(
                key_to_node_id[source_key],
                key_to_node_id[target_key],
                direction=connector["direction"],
                palette=palette,
                source_slot=source_groups[source_key].index(connector),
                source_total=len(source_groups[source_key]),
                target_slot=target_groups[target_key].index(connector),
                target_total=len(target_groups[target_key]),
                shape=connector.get("shape"),
                dashed=connector["dashed"],
            )
        )
    return built


def _build_layered_payload(groups: list[dict[str, Any]], palette: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    base_y = 70
    band_gap = 8
    section_padding = 25
    label_height = 36
    current_region_y = base_y
    for group_index, group in enumerate(groups):
        nodes = _string_list(group.get("nodes"))
        if not nodes:
            continue
        section_title = _shorten_layered_section_title(str(group.get("title") or f"分组 {group_index + 1}"))
        size_pairs = [estimate_node_size(text) for text in nodes]
        widths = [width for width, _ in size_pairs]
        heights = [height for _, height in size_pairs]
        total_width = sum(widths) + max(0, len(widths) - 1) * 60
        canvas_width = max(800, total_width + 100)
        max_height = max(heights)
        region_y = current_region_y
        label_y = region_y + 12
        node_y = region_y + 54
        positions = build_variable_row_positions(widths, canvas_width=canvas_width, gap=60, y=node_y)
        min_x = min(position[0] for position in positions)
        max_x = max(position[0] + widths[index] for index, position in enumerate(positions))
        region_width = max_x - min_x + section_padding * 2
        region_height = label_height + max_height + 42
        entries.append(
            {
                "key": f"bg{group_index}",
                "node": build_background_region(
                    str(group.get("title") or f"分组 {group_index + 1}"),
                    x=min_x - section_padding,
                    y=region_y,
                    width=region_width,
                    height=region_height,
                    palette=palette,
                    group_index=group_index,
                ),
            }
        )
        entries.append(
            {
                "key": f"label{group_index}",
                "node": build_section_label(
                    section_title,
                    x=min_x - section_padding + 12,
                    y=label_y,
                ),
            }
        )
        for node_index, text in enumerate(nodes):
            x, y = positions[node_index]
            width, height = size_pairs[node_index]
            entries.append(
                {
                    "key": f"g{group_index}n{node_index}",
                    "node": build_shape_node(
                        text,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        palette=palette,
                        group_index=group_index,
                    ),
                }
            )
        current_region_y = region_y + region_height + band_gap
    return entries


def _build_matrix_payload(groups: list[dict[str, Any]], palette: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not groups:
        return entries
    group = groups[0]
    columns = _string_list(group.get("columns"))
    rows = group.get("rows") if isinstance(group.get("rows"), list) else []
    if not columns or not rows:
        return entries

    normalized_rows: list[list[str]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        normalized_rows.append([str(value) for value in row[: len(columns)]])
    if not normalized_rows:
        return entries

    col_gap = 20
    row_gap = 15
    start_x = 100
    start_y = 80
    all_rows = [columns, *normalized_rows]
    col_widths: list[int] = []
    for col_index in range(len(columns)):
        widths = []
        for row in all_rows:
            if col_index >= len(row):
                continue
            width, _ = estimate_node_size(str(row[col_index]))
            widths.append(width)
        col_widths.append(max(150, max(widths, default=150)))

    row_heights: list[int] = []
    for row_index, row in enumerate(all_rows):
        heights = []
        for value in row:
            _, height = estimate_node_size(str(value))
            heights.append(height)
        safe_height = max(heights, default=NODE_SINGLE_LINE_SAFE_HEIGHT)
        if row_index == 0:
            safe_height = max(safe_height, NODE_DOUBLE_LINE_SAFE_HEIGHT)
        row_heights.append(safe_height)

    positions: list[list[tuple[int, int]]] = []
    current_y = start_y
    for row_index, row in enumerate(all_rows):
        current_x = start_x
        position_row: list[tuple[int, int]] = []
        for col_index, _ in enumerate(columns):
            position_row.append((current_x, current_y))
            current_x += col_widths[col_index] + col_gap
        positions.append(position_row)
        current_y += row_heights[row_index] + row_gap

    for col_index, title in enumerate(columns):
        x, y = positions[0][col_index]
        entries.append(
            {
                "key": f"g0h{col_index}",
                "node": build_shape_node(
                    title,
                    x=x,
                    y=y,
                    width=col_widths[col_index],
                    height=row_heights[0],
                    palette=palette,
                    group_index=0,
                    kind="accent",
                ),
            }
        )
    for row_index, row in enumerate(normalized_rows, start=1):
        for col_index, value in enumerate(row):
            x, y = positions[row_index][col_index]
            entries.append(
                {
                    "key": f"g0n{row_index - 1}_{col_index}",
                    "node": build_shape_node(
                        value,
                        x=x,
                        y=y,
                        width=col_widths[col_index],
                        height=row_heights[row_index],
                        palette=palette,
                        group_index=min(col_index, 4),
                    ),
                }
            )
    return entries


def _build_tree_payload(groups: list[dict[str, Any]], palette: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not groups:
        return entries
    group = groups[0]
    root_text = str(group.get("root") or "根节点")
    children = _string_list(group.get("children"))
    child_groups = group.get("child_groups") if isinstance(group.get("child_groups"), list) else []
    grouped_children: dict[str, list[str]] = {}
    for child_group in child_groups:
        if not isinstance(child_group, dict):
            continue
        parent_text = str(child_group.get("parent") or "")
        grouped_children[parent_text] = _string_list(child_group.get("children"))[:2]

    parent_sizes = [estimate_node_size(text) for text in children]
    parent_widths = [max(180, width) for width, _ in parent_sizes]
    parent_heights = [max(55, height) for _, height in parent_sizes]
    grandchild_size_map: dict[str, tuple[int, int]] = {}
    for values in grouped_children.values():
        for grandchild in values:
            width, height = estimate_node_size(grandchild)
            grandchild_size_map[grandchild] = (max(180, width), max(55, height))
    tree_gap = 60
    subtree_gap = 40

    subtree_widths: list[int] = []
    for child_index, child_text in enumerate(children):
        grand_children = grouped_children.get(child_text, [])
        grandchild_total_width = (
            sum(grandchild_size_map[grandchild][0] for grandchild in grand_children)
            + max(0, len(grand_children) - 1) * tree_gap
        )
        subtree_widths.append(max(parent_widths[child_index], grandchild_total_width))

    total_subtree_width = sum(subtree_widths) + max(0, len(subtree_widths) - 1) * subtree_gap
    canvas_width = max(800, total_subtree_width + 120)
    root_width, root_height = estimate_node_size(root_text)
    root_width = max(200, root_width)
    root_height = max(55, root_height)
    title_y = 20
    title_height = TITLE_SAFE_HEIGHT
    root_y = title_y + title_height + 30
    child_y = root_y + root_height + 65

    root_x = int(round((canvas_width - root_width) / 2))
    root = build_shape_node(
        root_text,
        x=root_x,
        y=root_y,
        width=root_width,
        height=root_height,
        palette=palette,
        group_index=0,
        kind="independent",
    )
    entries.append({"key": "g0n0", "node": root})

    positions: list[tuple[int, int]] = []
    start_subtree_x = int(round((canvas_width - total_subtree_width) / 2))
    current_subtree_x = start_subtree_x
    for child_index, subtree_width in enumerate(subtree_widths):
        node_x = current_subtree_x + int(round((subtree_width - parent_widths[child_index]) / 2))
        positions.append((node_x, child_y))
        current_subtree_x += subtree_width + subtree_gap

    for index, text in enumerate(children):
        x, y = positions[index]
        entries.append(
            {
                "key": f"g1n{index}",
                "node": build_shape_node(
                    text,
                    x=x,
                    y=y,
                    width=parent_widths[index],
                    height=parent_heights[index],
                    palette=palette,
                    group_index=index,
                ),
            }
        )
    split_grandchild_rows = sum(len(grouped_children.get(child_text, [])) for child_text in children) > 5
    midpoint = max(1, (len(children) + 1) // 2)

    for parent_index, child_group in enumerate(child_groups):
        if not isinstance(child_group, dict):
            continue
        parent_text = str(child_group.get("parent") or "")
        if parent_text not in children:
            continue
        parent_position_index = children.index(parent_text)
        parent_x, _ = positions[parent_position_index]
        grand_children = _string_list(child_group.get("children"))[:2]
        subtree_width = subtree_widths[parent_position_index]
        subtree_x = parent_x - int(round((subtree_width - parent_widths[parent_position_index]) / 2))
        grandchild_total_width = sum(grandchild_size_map[grandchild][0] for grandchild in grand_children) + max(
            0, len(grand_children) - 1
        ) * tree_gap
        grand_start_x = subtree_x + int(round((subtree_width - grandchild_total_width) / 2))
        grandchild_y = child_y + parent_heights[parent_position_index] + 55
        if split_grandchild_rows and parent_position_index >= midpoint:
            grandchild_y += 110
        grand_positions: list[tuple[int, int]] = []
        current_x = grand_start_x
        for grandchild in grand_children:
            grand_positions.append((current_x, grandchild_y))
            current_x += grandchild_size_map[grandchild][0] + tree_gap
        for child_index, child_text in enumerate(grand_children):
            x, y = grand_positions[child_index]
            grandchild_width, grandchild_height = grandchild_size_map[child_text]
            entries.append(
                {
                    "key": f"g2n{parent_index}_{child_index}",
                    "node": build_shape_node(
                        child_text,
                        x=x,
                        y=y,
                        width=grandchild_width,
                        height=grandchild_height,
                        palette=palette,
                        group_index=parent_position_index,
                    ),
                }
            )

    background_entries: list[dict[str, Any]] = []
    padding = 25
    for parent_index, child_text in enumerate(children):
        parent_x, parent_y = positions[parent_index]
        min_x = parent_x
        max_x = parent_x + parent_widths[parent_index]
        min_y = parent_y
        max_y = parent_y + parent_heights[parent_index]

        for child_group_index, child_group in enumerate(child_groups):
            if not isinstance(child_group, dict):
                continue
            if str(child_group.get("parent") or "") != child_text:
                continue
            grand_children = _string_list(child_group.get("children"))[:2]
            for grandchild_index, _ in enumerate(grand_children):
                key = f"g2n{child_group_index}_{grandchild_index}"
                matching = next((entry for entry in entries if entry["key"] == key), None)
                if matching is None:
                    continue
                node = matching["node"]
                min_x = min(min_x, int(node["x"]))
                max_x = max(max_x, int(node["x"]) + int(node["width"]))
                min_y = min(min_y, int(node["y"]))
                max_y = max(max_y, int(node["y"]) + int(node["height"]))

        background_entries.append(
            {
                "key": f"bg{parent_index}",
                "node": build_background_region(
                    "",
                    x=min_x - padding,
                    y=min_y - padding,
                    width=(max_x - min_x) + padding * 2,
                    height=(max_y - min_y) + padding * 2,
                    palette=palette,
                    group_index=parent_index,
                ),
            }
        )

    entries[1:1] = background_entries
    return entries


def _build_island_payload(groups: list[dict[str, Any]], palette: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    anchor_positions = [(40, 70), (430, 70), (40, 330), (430, 330)]
    for group_index, group in enumerate(groups[:4]):
        x, y = anchor_positions[group_index]
        nodes = _string_list(group.get("nodes"))[:3]
        node_sizes = [estimate_node_size(text) for text in nodes]
        node_widths = [max(120, width) for width, _ in node_sizes]
        node_heights = [max(40, height) for _, height in node_sizes]
        island_positions = [
            (x + 30, y + 55),
            (x + 30 + node_widths[0] + 20 if len(node_widths) > 1 else x + 170, y + 55),
            (x + 100, y + 55 + max(node_heights[:2], default=40) + 20),
        ]
        content_right = max(
            (island_positions[index][0] + node_widths[index] for index in range(len(nodes))),
            default=x + 250,
        )
        content_bottom = max(
            (island_positions[index][1] + node_heights[index] for index in range(len(nodes))),
            default=y + 125,
        )
        region_width = max(300, content_right - x + 30)
        region_height = max(170, content_bottom - y + 25)
        entries.append(
            {
                "key": f"bg{group_index}",
                "node": build_background_region(
                    str(group.get("title") or f"模块 {group_index + 1}"),
                    x=x,
                    y=y,
                    width=region_width,
                    height=region_height,
                    palette=palette,
                    group_index=group_index,
                ),
            }
        )
        entries.append(
            {
                "key": f"label{group_index}",
                "node": build_section_label(
                    str(group.get("title") or f"模块 {group_index + 1}"),
                    x=x + 12,
                    y=y + 12,
                ),
            }
        )
        for node_index, text in enumerate(nodes):
            node_x, node_y = island_positions[node_index]
            entries.append(
                {
                    "key": f"g{group_index}n{node_index}",
                    "node": build_shape_node(
                        text,
                        x=node_x,
                        y=node_y,
                        width=node_widths[node_index],
                        height=node_heights[node_index],
                        palette=palette,
                        group_index=group_index,
                    ),
                }
            )
    return entries


def _build_free_payload(groups: list[dict[str, Any]], palette: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not groups:
        return entries
    nodes = _string_list(groups[0].get("nodes"))
    free_positions = [(320, 210), (70, 110), (130, 310), (560, 120), (360, 40)]
    for index, text in enumerate(nodes[: len(free_positions)]):
        x, y = free_positions[index]
        entries.append(
            {
                "key": f"g0n{index}",
                "node": build_shape_node(
                    text,
                    x=x,
                    y=y,
                    palette=palette,
                    group_index=min(index, 4),
                ),
            }
        )
    return entries


def _select_representative_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(edges) <= 8:
        return list(edges)
    max_edges = 8
    selected: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    def append_edge(edge: dict[str, Any]) -> None:
        source = str(edge.get("from") or "")
        target = str(edge.get("to") or "")
        pair = (source, target)
        if not source or not target or pair in seen_pairs:
            return
        selected.append(edge)
        seen_pairs.add(pair)

    seen_sources: set[str] = set()
    for edge in edges:
        source = str(edge.get("from") or "")
        if source and source not in seen_sources:
            append_edge(edge)
            seen_sources.add(source)
        if len(selected) >= max_edges:
            return selected[:max_edges]

    seen_targets: set[str] = set()
    for edge in edges:
        target = str(edge.get("to") or "")
        if target and target not in seen_targets:
            append_edge(edge)
            seen_targets.add(target)
        if len(selected) >= max_edges:
            return selected[:max_edges]

    for edge in edges:
        append_edge(edge)
        if len(selected) >= max_edges:
            break
    return selected[:max_edges]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _infer_title(message: str) -> str:
    stripped = message.strip()
    if not stripped:
        return "Feishu Board"
    matched = None
    for pattern in (
        r"(?:帮我|请|请帮我)?(?:画|做|生成)(?:一个|一张|一份)?(.+?)(?:，|,|需要|要求|并体现|并突出|并展示|$)",
        r"(.+?)(?:，|,|需要|要求|并体现|并突出|并展示|$)",
    ):
        matched = re.search(pattern, stripped)
        if matched:
            candidate = matched.group(1).strip()
            if candidate:
                return _clean_inferred_title(candidate)
    return _clean_inferred_title(stripped)


def _clean_inferred_title(value: str) -> str:
    title = value.strip()
    title = re.sub(r"^(一个|一张|一份)", "", title)
    title = re.sub(r"^(完整详细的|完整的|详细的|简单的|简版的|完整详细|完整|详细|简单)", "", title)
    title = re.sub(r"(需要.*|要求.*|并体现.*|并突出.*|并展示.*)$", "", title).strip(" ，,。")
    return title or "Feishu Board"


def _infer_detail_level(message: str) -> str:
    normalized = _normalize_text(message)
    if any(keyword in normalized for keyword in ("简单", "简版", "概览", "概述")):
        return "simple"
    if any(keyword in normalized for keyword in ("完整", "详细", "细化", "深入", "全量")):
        return "detailed"
    return "normal"


def _layered_groups_for_detail(detail_level: str) -> list[dict[str, Any]]:
    if detail_level == "simple":
        return [
            {"title": "接入层", "nodes": ["Web 应用\n用户入口", "开放接口\n外部接入"]},
            {"title": "服务层", "nodes": ["API 网关\n统一转发", "业务服务\n请求处理", "Agent 服务\n任务执行"]},
            {"title": "数据层", "nodes": ["向量库\n知识检索", "对象存储\n文件归档"]},
        ]
    if detail_level == "detailed":
        return [
            {"title": "接入层", "nodes": ["Web 应用\n用户入口", "移动端\n多端访问", "开放接口\n生态接入", "管理后台\n运维配置"]},
            {"title": "网关层", "nodes": ["API 网关\n统一转发", "鉴权中心\n权限校验", "限流服务\n流量控制", "审计服务\n访问留痕"]},
            {"title": "编排层", "nodes": ["流程编排\n任务拆解", "任务调度\n执行编排", "Agent 服务\n工具调用", "知识编排\n上下文组织"]},
            {"title": "模型层", "nodes": ["模型路由\n模型分发", "Embedding\n向量生成", "重排服务\n结果优化", "评测服务\n质量校验"]},
            {"title": "数据层", "nodes": ["向量库\n知识检索", "对象存储\n文件归档", "日志监控\n运行观测", "元数据仓\n索引管理"]},
        ]
    return [
        {"title": "接入层", "nodes": ["Web 应用\n用户入口", "移动端\n多端访问", "开放接口\n外部接入"]},
        {"title": "服务层", "nodes": ["API 网关\n统一转发", "编排服务\n流程控制", "Agent 服务\n任务执行"]},
        {"title": "模型层", "nodes": ["模型路由\n模型分发", "Embedding\n向量生成", "重排服务\n结果优化"]},
        {"title": "数据层", "nodes": ["向量库\n知识检索", "对象存储\n文件归档", "日志监控\n运行观测"]},
    ]


def _build_layered_edges(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for group_index in range(len(groups) - 1):
        source_nodes = _string_list(groups[group_index].get("nodes"))
        target_nodes = _string_list(groups[group_index + 1].get("nodes"))
        if not source_nodes or not target_nodes:
            continue
        edge_budget = min(max(len(source_nodes), len(target_nodes)), 8 - len(edges))
        if edge_budget <= 0:
            break
        for node_index in range(edge_budget):
            source_key = f"g{group_index}n{node_index % len(source_nodes)}"
            target_key = f"g{group_index + 1}n{node_index % len(target_nodes)}"
            edges.append({"from": source_key, "to": target_key, "direction": "tb"})
    return edges


def _merge_small_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    bucket: dict[str, Any] | None = None
    for group in groups:
        nodes = _string_list(group.get("nodes"))
        if bucket is None:
            bucket = {"title": str(group.get("title") or ""), "nodes": nodes}
            continue
        current_nodes = _string_list(bucket.get("nodes"))
        if len(current_nodes) < 2 and len(current_nodes) + len(nodes) <= 5:
            bucket["title"] = f'{bucket["title"]}/{group.get("title")}'
            bucket["nodes"] = current_nodes + nodes
            continue
        merged.append(bucket)
        bucket = {"title": str(group.get("title") or ""), "nodes": nodes}
    if bucket is not None:
        merged.append(bucket)
    return merged
