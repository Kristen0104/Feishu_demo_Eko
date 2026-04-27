from __future__ import annotations

from copy import deepcopy
from typing import Any


CLEAN_FLOW_TEMPLATE = {
    "start": {
        "shape_kind": "state_start",
        "style": {
            "fill_color": "#e7f8ef",
            "border_color": "#16a34a",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 14,
    },
    "end": {
        "shape_kind": "state_end",
        "style": {
            "fill_color": "#eef2ff",
            "border_color": "#4f46e5",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 14,
    },
    "decision": {
        "shape_kind": "flow_chart_diamond",
        "style": {
            "fill_color": "#fff7ed",
            "border_color": "#f59e0b",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 13,
    },
    "step": {
        "shape_kind": "flow_chart_round_rect",
        "style": {
            "fill_color": "#eff6ff",
            "border_color": "#2563eb",
            "border_style": "solid",
            "border_width": "narrow",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "regular",
        "font_size": 13,
    },
    "branch": {
        "shape_kind": "flow_chart_round_rect",
        "style": {
            "fill_color": "#f5f3ff",
            "border_color": "#7c3aed",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "regular",
        "font_size": 13,
    },
    "edge": {
        "shape": "right_angled_polyline",
        "arrow_style": "triangle_arrow",
        "style": {
            "border_color": "#9ca3af",
            "border_style": "solid",
            "border_width": "narrow",
            "border_opacity": 100,
        },
    },
}

SUNSET_FLOW_TEMPLATE = {
    "start": {
        "shape_kind": "state_start",
        "style": {
            "fill_color": "#ffedd5",
            "border_color": "#f97316",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 14,
    },
    "end": {
        "shape_kind": "state_end",
        "style": {
            "fill_color": "#fee2e2",
            "border_color": "#dc2626",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 14,
    },
    "decision": {
        "shape_kind": "flow_chart_diamond",
        "style": {
            "fill_color": "#fff7ed",
            "border_color": "#f59e0b",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 13,
    },
    "step": {
        "shape_kind": "flow_chart_round_rect",
        "style": {
            "fill_color": "#fff1f2",
            "border_color": "#e11d48",
            "border_style": "solid",
            "border_width": "narrow",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "regular",
        "font_size": 13,
    },
    "branch": {
        "shape_kind": "flow_chart_round_rect",
        "style": {
            "fill_color": "#fef3c7",
            "border_color": "#d97706",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "regular",
        "font_size": 13,
    },
    "edge": {
        "shape": "right_angled_polyline",
        "arrow_style": "triangle_arrow",
        "style": {
            "border_color": "#d97706",
            "border_style": "solid",
            "border_width": "narrow",
            "border_opacity": 100,
        },
    },
}

FOREST_FLOW_TEMPLATE = {
    "start": {
        "shape_kind": "state_start",
        "style": {
            "fill_color": "#d1fae5",
            "border_color": "#059669",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 14,
    },
    "end": {
        "shape_kind": "state_end",
        "style": {
            "fill_color": "#ecfeff",
            "border_color": "#0891b2",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 14,
    },
    "decision": {
        "shape_kind": "flow_chart_diamond",
        "style": {
            "fill_color": "#fef9c3",
            "border_color": "#ca8a04",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 13,
    },
    "step": {
        "shape_kind": "flow_chart_round_rect",
        "style": {
            "fill_color": "#ccfbf1",
            "border_color": "#0f766e",
            "border_style": "solid",
            "border_width": "narrow",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "regular",
        "font_size": 13,
    },
    "branch": {
        "shape_kind": "flow_chart_round_rect",
        "style": {
            "fill_color": "#ecfccb",
            "border_color": "#65a30d",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "regular",
        "font_size": 13,
    },
    "edge": {
        "shape": "right_angled_polyline",
        "arrow_style": "triangle_arrow",
        "style": {
            "border_color": "#0f766e",
            "border_style": "solid",
            "border_width": "narrow",
            "border_opacity": 100,
        },
    },
}

MONO_EXEC_TEMPLATE = {
    "start": {
        "shape_kind": "state_start",
        "style": {
            "fill_color": "#f1f5f9",
            "border_color": "#475569",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 14,
    },
    "end": {
        "shape_kind": "state_end",
        "style": {
            "fill_color": "#e2e8f0",
            "border_color": "#0f172a",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 14,
    },
    "decision": {
        "shape_kind": "flow_chart_diamond",
        "style": {
            "fill_color": "#f8fafc",
            "border_color": "#64748b",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "bold",
        "font_size": 13,
    },
    "step": {
        "shape_kind": "flow_chart_round_rect",
        "style": {
            "fill_color": "#dbeafe",
            "border_color": "#2563eb",
            "border_style": "solid",
            "border_width": "narrow",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "regular",
        "font_size": 13,
    },
    "branch": {
        "shape_kind": "flow_chart_round_rect",
        "style": {
            "fill_color": "#e0e7ff",
            "border_color": "#4f46e5",
            "border_style": "solid",
            "border_width": "medium",
            "fill_opacity": 100,
            "border_opacity": 100,
        },
        "font_weight": "regular",
        "font_size": 13,
    },
    "edge": {
        "shape": "right_angled_polyline",
        "arrow_style": "triangle_arrow",
        "style": {
            "border_color": "#64748b",
            "border_style": "solid",
            "border_width": "narrow",
            "border_opacity": 100,
        },
    },
}

STYLE_TEMPLATES = {
    "clean_flow": CLEAN_FLOW_TEMPLATE,
    "sunset_flow": SUNSET_FLOW_TEMPLATE,
    "forest_flow": FOREST_FLOW_TEMPLATE,
    "mono_exec": MONO_EXEC_TEMPLATE,
}


def apply_canvas_style_template(
    snapshot: dict[str, Any],
    *,
    template_name: str = "clean_flow",
    style_plan: dict[str, Any] | None = None,
    override_existing_styles: bool = False,
) -> dict[str, Any]:
    resolved_template_name = _resolve_template_name(
        template_name=template_name,
        style_plan=style_plan,
    )
    template = STYLE_TEMPLATES[resolved_template_name]

    styled = deepcopy(snapshot)
    nodes = styled.get("nodes", [])
    edges = styled.get("edges", [])
    if isinstance(nodes, list):
        branch_node_ids = _branch_node_ids(edges)
        styled["nodes"] = [
            _style_node(
                node,
                template=template,
                branch_node_ids=branch_node_ids,
                override_existing_styles=override_existing_styles,
            )
            if isinstance(node, dict)
            else node
            for node in nodes
        ]
    if isinstance(edges, list):
        styled["edges"] = [
            _style_edge(
                edge,
                template=template,
                override_existing_styles=override_existing_styles,
            )
            if isinstance(edge, dict)
            else edge
            for edge in edges
        ]
    styled.setdefault("style_template", resolved_template_name)
    return styled


def _style_node(
    node: dict[str, Any],
    *,
    template: dict[str, dict[str, Any]],
    branch_node_ids: set[str],
    override_existing_styles: bool,
) -> dict[str, Any]:
    role = _node_role(node, branch_node_ids=branch_node_ids)
    defaults = template[role]
    styled = dict(node)
    if role in {"start", "end", "decision"}:
        styled.setdefault("visual_role", role)
    styled.setdefault("shape_kind", defaults["shape_kind"])
    styled["style"] = _merge_style(
        defaults["style"],
        styled.get("style"),
        override_existing_styles=override_existing_styles,
    )
    styled.setdefault("font_size", defaults["font_size"])
    styled.setdefault("font_weight", defaults["font_weight"])
    styled.setdefault("horizontal_align", "center")
    styled.setdefault("vertical_align", "mid")
    return styled


def _style_edge(
    edge: dict[str, Any],
    *,
    template: dict[str, dict[str, Any]],
    override_existing_styles: bool,
) -> dict[str, Any]:
    defaults = template["edge"]
    styled = dict(edge)
    styled.setdefault("shape", defaults["shape"])
    styled.setdefault("arrow_style", defaults["arrow_style"])
    styled["style"] = _merge_style(
        defaults["style"],
        styled.get("style"),
        override_existing_styles=override_existing_styles,
    )
    return styled


def _merge_style(
    default_style: dict[str, Any],
    existing_style: object,
    *,
    override_existing_styles: bool,
) -> dict[str, Any]:
    merged = dict(default_style)
    if isinstance(existing_style, dict):
        existing = {
            key: value
            for key, value in existing_style.items()
            if value not in (None, "")
        }
        if override_existing_styles:
            return {**existing, **merged}
        merged.update(existing)
    return merged


def _resolve_template_name(
    *,
    template_name: str,
    style_plan: dict[str, Any] | None,
) -> str:
    candidate = template_name
    if isinstance(style_plan, dict):
        candidate = str(style_plan.get("template") or candidate).strip()
    return candidate if candidate in STYLE_TEMPLATES else "clean_flow"


def _branch_node_ids(edges: object) -> set[str]:
    if not isinstance(edges, list):
        return set()
    branch_ids = set()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        label = str(edge.get("label", "")).strip().lower()
        if label in {"否", "no", "n", "false", "等待", "返回", "重试", "retry"}:
            to_id = str(edge.get("to", "")).strip()
            if to_id:
                branch_ids.add(to_id)
    return branch_ids


def _node_role(node: dict[str, Any], *, branch_node_ids: set[str]) -> str:
    node_id = str(node.get("id", "")).strip()
    visual_role = str(node.get("visual_role", "")).strip()
    if visual_role in {"start", "end", "decision"}:
        return visual_role
    shape_kind = str(node.get("shape_kind", node.get("shape", ""))).strip()
    if shape_kind == "flow_chart_diamond":
        return "decision"
    text = str(node.get("text", "")).strip()
    lower_text = text.lower()
    if text.startswith("开始") or lower_text.startswith("start"):
        return "start"
    if text.endswith("结束") or text.endswith("完成") or lower_text.endswith("end"):
        return "end"
    if node_id in branch_node_ids:
        return "branch"
    return "step"
