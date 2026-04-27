from __future__ import annotations

from typing import Any

from app.modules.feishu.schemas import FeishuBoardAdapterPayloadSchema


PASSTHROUGH_NODE_TYPES = {
    "composite_shape",
    "text_shape",
    "connector",
    "table",
    "group",
    "table_uml",
    "table_er",
    "paint",
    "image",
    "svg",
    "life_line",
    "activation",
    "combined_fragment",
}


def build_publish_nodes(
    payload: FeishuBoardAdapterPayloadSchema,
) -> list[dict[str, Any]]:
    source_nodes = payload.source_board.nodes
    node_by_id = {
        str(node.get("id", "")).strip(): node
        for node in source_nodes
        if isinstance(node, dict) and str(node.get("id", "")).strip()
    }
    nodes = [
        build_publish_shape_node(node, index=index)
        for index, node in enumerate(source_nodes, start=1)
    ]
    connectors = [
        connector
        for edge in payload.source_board.edges
        if (
            connector := build_publish_connector(
                edge=edge,
                node_by_id=node_by_id,
            )
        )
        is not None
    ]
    return [*nodes, *connectors]


def build_publish_shape_node(
    node: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    node_type = str(node.get("type", "")).strip()
    if node_type == "section":
        return build_publish_section_node(node, index=index)
    if node_type == "sticky_note":
        return build_publish_sticky_note_node(node, index=index)
    if node_type == "mind_map":
        return build_publish_mind_map_node(node, index=index)
    if node_type in PASSTHROUGH_NODE_TYPES:
        return dict(node)

    node_id = str(node.get("id", f"node-{index}")).strip() or f"node-{index}"
    text = str(node.get("text", "")).strip()
    width = float(node.get("width", max(160, min(480, 40 + max(len(text), 1) * 14))))
    height = float(node.get("height", max(64, min(180, 56 + max(len(text), 1) * 3))))
    publish_node = {
        "id": node_id,
        "type": "composite_shape",
        "x": float(node.get("x", 120)),
        "y": float(node.get("y", 120 + ((index - 1) * 96))),
        "width": width,
        "height": height,
        "composite_shape": {
            "type": resolve_shape_kind(node),
        },
    }
    text_payload = build_publish_text(node, text)
    if text_payload:
        publish_node["text"] = text_payload
    style_payload = build_publish_style(node)
    if style_payload:
        publish_node["style"] = style_payload
    return publish_node


def build_base_publish_node(
    node: dict[str, Any],
    *,
    index: int,
    node_type: str,
    default_width: float,
    default_height: float,
) -> dict[str, Any]:
    node_id = str(node.get("id", f"node-{index}")).strip() or f"node-{index}"
    publish_node: dict[str, Any] = {
        "id": node_id,
        "type": node_type,
        "x": float(node.get("x", 120)),
        "y": float(node.get("y", 120 + ((index - 1) * 96))),
        "width": float(node.get("width", default_width)),
        "height": float(node.get("height", default_height)),
    }
    for key in ("parent_id", "locked", "z_index"):
        if key in node and node[key] not in (None, ""):
            publish_node[key] = node[key]
    if isinstance(node.get("angle"), (int, float)):
        publish_node["angle"] = float(node["angle"])
    return publish_node


def build_publish_section_node(
    node: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    publish_node = build_base_publish_node(
        node,
        index=index,
        node_type="section",
        default_width=480,
        default_height=240,
    )
    section = node.get("section") if isinstance(node.get("section"), dict) else {}
    title = str(node.get("title", section.get("title", node.get("text", "")))).strip()
    publish_node["section"] = {"title": title or "Section"}
    style_payload = build_publish_style(
        node,
        allowed_keys={
            "fill_color",
            "fill_opacity",
            "border_style",
            "border_width",
            "border_opacity",
            "theme_fill_color_code",
            "theme_border_color_code",
            "fill_color_type",
            "border_color_type",
        },
    )
    if style_payload:
        publish_node["style"] = style_payload
    return publish_node


def build_publish_sticky_note_node(
    node: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    publish_node = build_base_publish_node(
        node,
        index=index,
        node_type="sticky_note",
        default_width=240,
        default_height=180,
    )
    text_payload = build_publish_text(node, str(node.get("text", "")))
    if text_payload:
        publish_node["text"] = text_payload
    sticky_note = dict(node["sticky_note"]) if isinstance(node.get("sticky_note"), dict) else {}
    user_id = str(node.get("user_id", sticky_note.get("user_id", ""))).strip()
    if user_id:
        sticky_note["user_id"] = user_id
    if isinstance(node.get("show_author_info"), bool):
        sticky_note["show_author_info"] = bool(node["show_author_info"])
    if sticky_note:
        publish_node["sticky_note"] = sticky_note
    style_payload = build_publish_style(
        node,
        allowed_keys={
            "fill_color",
            "fill_opacity",
            "theme_fill_color_code",
            "fill_color_type",
        },
    )
    if style_payload:
        publish_node["style"] = style_payload
    return publish_node


def build_publish_mind_map_node(
    node: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    publish_node = build_base_publish_node(
        node,
        index=index,
        node_type="mind_map",
        default_width=180,
        default_height=60,
    )
    text_payload = build_publish_text(node, str(node.get("text", "")))
    if text_payload:
        publish_node["text"] = text_payload

    root_payload = node.get("mind_map_root")
    node_payload = node.get("mind_map_node")
    parent_id = str(node.get("parent_id", "")).strip()
    mind_map_role = str(node.get("mind_map_role", "")).strip()
    if isinstance(root_payload, dict):
        publish_node["mind_map_root"] = dict(root_payload)
    elif not parent_id and mind_map_role != "node":
        publish_node["mind_map_root"] = {
            "layout": str(node.get("mind_map_layout", node.get("layout", "left_right"))),
            "type": str(node.get("mind_map_type", "mind_map_round_rect")),
            "line_style": str(node.get("line_style", "round_angle")),
        }
    elif isinstance(node_payload, dict):
        publish_node["mind_map_node"] = dict(node_payload)
    else:
        publish_node["mind_map_node"] = {
            "parent_id": parent_id,
            "type": str(node.get("mind_map_type", "mind_map_text")),
        }
        if isinstance(node.get("z_index"), int):
            publish_node["mind_map_node"]["z_index"] = int(node["z_index"])
        layout_position = str(node.get("layout_position", "")).strip()
        if layout_position:
            publish_node["mind_map_node"]["layout_position"] = layout_position
        if isinstance(node.get("collapsed"), bool):
            publish_node["mind_map_node"]["collapsed"] = bool(node["collapsed"])
    return publish_node


def build_publish_connector(
    edge: dict[str, Any],
    *,
    node_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    start_id = str(edge.get("from", "")).strip()
    end_id = str(edge.get("to", "")).strip()
    if not start_id or not end_id:
        return None
    edge_id = str(edge.get("id", f"{start_id}-{end_id}")).strip() or f"{start_id}-{end_id}"
    connector: dict[str, Any] = {
        "start": build_connector_attachment(
            node_by_id.get(start_id),
            node_by_id.get(end_id),
            start=True,
            fallback_id=start_id,
            label=str(edge.get("label", edge.get("text", ""))).strip(),
            arrow_style=str(edge.get("start_arrow_style", "")).strip() or None,
        ),
        "end": build_connector_attachment(
            node_by_id.get(end_id),
            node_by_id.get(start_id),
            start=False,
            fallback_id=end_id,
            label=str(edge.get("label", edge.get("text", ""))).strip(),
            arrow_style=str(edge.get("end_arrow_style", edge.get("arrow_style", ""))).strip()
            or None,
        ),
        "shape": normalize_connector_shape(
            edge.get("shape"),
            edge=edge,
            node_by_id=node_by_id,
        ),
    }
    turning_points = edge.get("turning_points", edge.get("turningPoints"))
    if isinstance(turning_points, list):
        normalized_turning_points = [
            {"x": float(point["x"]), "y": float(point["y"])}
            for point in turning_points
            if isinstance(point, dict)
            and isinstance(point.get("x"), (int, float))
            and isinstance(point.get("y"), (int, float))
        ]
        if normalized_turning_points:
            connector["turning_points"] = normalized_turning_points
    captions = build_connector_captions(edge)
    if captions:
        connector["captions"] = captions
    if isinstance(edge.get("caption_auto_direction"), bool):
        connector["caption_auto_direction"] = bool(edge["caption_auto_direction"])
    if isinstance(edge.get("caption_position"), (int, float)):
        caption_position = float(edge["caption_position"])
        if 0 <= caption_position <= 1:
            connector["caption_position"] = caption_position
    elif is_same_row_return_edge(edge, node_by_id=node_by_id):
        connector["caption_position"] = 0.25
    style_payload = build_publish_style(edge)
    if style_payload:
        connector["style"] = style_payload
    return {
        "id": edge_id,
        "type": "connector",
        "connector": connector,
    }


def resolve_shape_kind(node: dict[str, Any]) -> str:
    explicit_shape = str(node.get("shape_kind", node.get("shape", ""))).strip()
    if explicit_shape:
        if explicit_shape in {"state_start", "state_end"}:
            return "flow_chart_round_rect"
        return explicit_shape
    visual_role = str(node.get("visual_role", node.get("role", ""))).strip()
    if visual_role in {"decision", "branch"}:
        return "flow_chart_diamond"
    if visual_role in {"start", "entry"}:
        return "state_start"
    if visual_role in {"end", "finish"}:
        return "state_end"
    if visual_role in {"data", "input", "output"}:
        return "flow_chart_parallelogram"
    if visual_role in {"note", "annotation"}:
        return "note_shape"
    semantic_type = str(node.get("semantic_type", "")).strip()
    if semantic_type in {"database", "storage"}:
        return "flow_chart_cylinder"
    node_type = str(node.get("type", "")).strip()
    if node_type == "topic":
        return "flow_chart_round_rect"
    return "round_rect"


def build_publish_text(node: dict[str, Any], fallback_text: str) -> dict[str, Any]:
    existing_text = node.get("text")
    if isinstance(existing_text, dict):
        payload = {
            key: value
            for key, value in existing_text.items()
            if value not in (None, "")
        }
        if isinstance(node.get("rich_text"), dict):
            payload["rich_text"] = dict(node["rich_text"])
        return payload

    text_value = str(node.get("text", fallback_text)).strip()
    if not text_value:
        return {}
    payload: dict[str, Any] = {
        "text": text_value,
        "horizontal_align": str(node.get("horizontal_align", "center")),
        "vertical_align": str(node.get("vertical_align", "mid")),
    }
    if str(node.get("text_angle", "")).strip():
        try:
            payload["angle"] = int(node["text_angle"])
        except (TypeError, ValueError):
            pass
    for key in ("font_size", "theme_text_color_code", "theme_text_background_color_code"):
        if isinstance(node.get(key), int):
            payload[key] = int(node[key])
    for key in ("font_weight", "text_color", "text_background_color"):
        if str(node.get(key, "")).strip():
            payload[key] = str(node[key])
    for key in ("italic", "underline", "line_through"):
        if isinstance(node.get(key), bool):
            payload[key] = bool(node[key])
    for key in ("text_color_type", "text_background_color_type"):
        if isinstance(node.get(key), int):
            payload[key] = int(node[key])
    if isinstance(node.get("rich_text"), dict):
        payload["rich_text"] = dict(node["rich_text"])
    return payload


def build_publish_style(
    node: dict[str, Any],
    *,
    allowed_keys: set[str] | None = None,
) -> dict[str, Any]:
    existing_style = node.get("style")
    if isinstance(existing_style, dict):
        return normalize_publish_style(existing_style, allowed_keys=allowed_keys)
    style_keys = {
        "fill_color",
        "fill_opacity",
        "border_style",
        "border_width",
        "border_opacity",
        "border_color",
        "theme_fill_color_code",
        "theme_border_color_code",
        "h_flip",
        "v_flip",
        "fill_color_type",
        "border_color_type",
    }
    if allowed_keys is not None:
        style_keys = style_keys.intersection(allowed_keys)
    return normalize_publish_style(
        {key: node[key] for key in style_keys if key in node},
        allowed_keys=style_keys,
    )


def normalize_publish_style(
    style: dict[str, Any],
    *,
    allowed_keys: set[str] | None = None,
) -> dict[str, Any]:
    style_keys = {
        "fill_color",
        "fill_opacity",
        "border_style",
        "border_width",
        "border_opacity",
        "border_color",
        "theme_fill_color_code",
        "theme_border_color_code",
        "h_flip",
        "v_flip",
        "fill_color_type",
        "border_color_type",
    }
    if allowed_keys is not None:
        style_keys = style_keys.intersection(allowed_keys)
    normalized: dict[str, Any] = {}
    for key in style_keys:
        if key not in style:
            continue
        value = style[key]
        if value in (None, ""):
            continue
        normalized_value = normalize_publish_style_value(key, value)
        if normalized_value is not None:
            normalized[key] = normalized_value
    return normalized


def normalize_publish_style_value(key: str, value: Any) -> Any | None:
    if key in {"fill_color", "border_color"}:
        return str(value).strip() if str(value).strip() else None
    if key == "border_style":
        border_style = str(value).strip()
        return border_style if border_style in {"solid", "dash", "dot"} else None
    if key == "border_width":
        border_width = str(value).strip()
        return border_width if border_width in {"narrow", "medium", "wide"} else None
    if key in {"fill_opacity", "border_opacity"}:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0, min(100, int(value)))
        return None
    if key in {
        "theme_fill_color_code",
        "theme_border_color_code",
        "fill_color_type",
        "border_color_type",
    }:
        return int(value) if isinstance(value, int) and not isinstance(value, bool) else None
    if key in {"h_flip", "v_flip"}:
        return bool(value) if isinstance(value, bool) else None
    return None


def build_connector_attachment(
    primary_node: dict[str, Any] | None,
    secondary_node: dict[str, Any] | None,
    *,
    start: bool,
    fallback_id: str,
    label: str = "",
    arrow_style: str | None = None,
) -> dict[str, Any]:
    snap_to = infer_snap_to(
        primary_node,
        secondary_node,
        label=label,
        start=start,
    )
    return {
        "attached_object": {
            "id": fallback_id,
            "snap_to": snap_to,
            "position": connector_attachment_position(
                primary_node=primary_node,
                secondary_node=secondary_node,
                snap_to=snap_to,
            ),
        },
        "arrow_style": normalize_arrow_style(
            arrow_style,
            fallback="none" if start else "triangle_arrow",
        ),
    }


def normalize_connector_shape(
    value: Any,
    *,
    edge: dict[str, Any] | None = None,
    node_by_id: dict[str, dict[str, Any]] | None = None,
) -> str:
    allowed_shapes = {"straight", "polyline", "curve", "right_angled_polyline"}
    shape = str(value or "").strip()
    if edge is not None and node_by_id is not None and is_same_row_return_edge(
        edge,
        node_by_id=node_by_id,
    ) and shape in {"", "polyline", "right_angled_polyline"}:
        return "curve"
    if shape in allowed_shapes:
        return shape
    if edge is not None and node_by_id is not None and is_same_row_return_edge(
        edge,
        node_by_id=node_by_id,
    ):
        return "curve"
    return "right_angled_polyline"


def is_same_row_return_edge(
    edge: dict[str, Any],
    *,
    node_by_id: dict[str, dict[str, Any]],
) -> bool:
    if not is_return_label(str(edge.get("label", edge.get("text", "")))):
        return False
    from_node = node_by_id.get(str(edge.get("from", "")).strip())
    to_node = node_by_id.get(str(edge.get("to", "")).strip())
    if not isinstance(from_node, dict) or not isinstance(to_node, dict):
        return False
    from_cx, from_cy, to_cx, to_cy = node_center_pair(from_node, to_node)
    vertical_gap = abs(to_cy - from_cy)
    max_height = max_node_height(from_node, to_node)
    return to_cx < from_cx and vertical_gap < max_height * 0.7


def normalize_arrow_style(value: str | None, *, fallback: str) -> str:
    allowed_arrow_styles = {
        "none",
        "line_arrow",
        "triangle_arrow",
        "empty_triangle_arrow",
        "circle_arrow",
        "empty_circle_arrow",
        "diamond_arrow",
        "empty_diamond_arrow",
        "single_arrow",
        "multi_arrow",
        "exact_single_arrow",
        "zero_or_multi_arrow",
        "zero_or_single_arrow",
        "single_or_multi_arrow",
        "x_arrow",
    }
    arrow_style = str(value or "").strip()
    if arrow_style in allowed_arrow_styles:
        return arrow_style
    return fallback


def snap_to_position(snap_to: str) -> dict[str, float]:
    if snap_to == "left":
        return {"x": 0.0, "y": 0.5}
    if snap_to == "right":
        return {"x": 1.0, "y": 0.5}
    if snap_to == "top":
        return {"x": 0.5, "y": 0.0}
    if snap_to == "bottom":
        return {"x": 0.5, "y": 1.0}
    return {"x": 0.5, "y": 0.5}


def connector_attachment_position(
    primary_node: dict[str, Any] | None,
    secondary_node: dict[str, Any] | None,
    *,
    snap_to: str,
) -> dict[str, float]:
    position = snap_to_position(snap_to)
    if not isinstance(primary_node, dict) or not isinstance(secondary_node, dict):
        return position
    if is_diamond_node(primary_node):
        return position
    primary_x = float(primary_node.get("x", 0) or 0)
    primary_y = float(primary_node.get("y", 0) or 0)
    primary_width = float(primary_node.get("width", 220) or 220)
    primary_height = float(primary_node.get("height", 100) or 100)
    secondary_cx = float(secondary_node.get("x", 0) or 0) + (
        float(secondary_node.get("width", 220) or 220) / 2
    )
    secondary_cy = float(secondary_node.get("y", 0) or 0) + (
        float(secondary_node.get("height", 100) or 100) / 2
    )
    primary_cx = primary_x + primary_width / 2
    primary_cy = primary_y + primary_height / 2
    if snap_to in {"top", "bottom"} and primary_width > 0:
        shared_x = (primary_cx + secondary_cx) / 2
        position["x"] = _clamp_unit((shared_x - primary_x) / primary_width)
    if snap_to in {"left", "right"} and primary_height > 0:
        shared_y = (primary_cy + secondary_cy) / 2
        position["y"] = _clamp_unit((shared_y - primary_y) / primary_height)
    return position


def is_diamond_node(node: dict[str, Any]) -> bool:
    shape = str(node.get("shape_kind", node.get("shape", ""))).strip()
    visual_role = str(node.get("visual_role", node.get("role", ""))).strip()
    return shape == "flow_chart_diamond" or visual_role in {"decision", "branch"}


def infer_snap_to(
    primary_node: dict[str, Any] | None,
    secondary_node: dict[str, Any] | None,
    *,
    label: str = "",
    start: bool = True,
) -> str:
    if not isinstance(primary_node, dict) or not isinstance(secondary_node, dict):
        return "right"
    primary_cx, primary_cy, secondary_cx, secondary_cy = node_center_pair(
        primary_node,
        secondary_node,
    )
    dx = secondary_cx - primary_cx
    dy = secondary_cy - primary_cy
    if is_return_label(label) and abs(dy) < max_node_height(primary_node, secondary_node) * 0.7:
        return "bottom"
    branch_snap = branch_label_snap_to(label, start=start, dx=dx, dy=dy)
    if branch_snap:
        return branch_snap
    if abs(dx) >= abs(dy):
        return "right" if dx >= 0 else "left"
    if dy >= 0:
        return "bottom"
    return "top"


def node_center_pair(
    primary_node: dict[str, Any],
    secondary_node: dict[str, Any],
) -> tuple[float, float, float, float]:
    primary_cx = float(primary_node.get("x", 0)) + float(primary_node.get("width", 220)) / 2
    primary_cy = float(primary_node.get("y", 0)) + float(primary_node.get("height", 100)) / 2
    secondary_cx = float(secondary_node.get("x", 0)) + float(secondary_node.get("width", 220)) / 2
    secondary_cy = float(secondary_node.get("y", 0)) + float(secondary_node.get("height", 100)) / 2
    return primary_cx, primary_cy, secondary_cx, secondary_cy


def branch_label_snap_to(label: str, *, start: bool, dx: float, dy: float) -> str | None:
    normalized = str(label or "").strip().lower()
    if normalized in {"是", "yes", "y", "true", "通过"} and (
        (start and dx >= 0) or (not start and dx <= 0)
    ):
        return "right" if start else "left"
    if normalized in {"否", "no", "n", "false", "不通过", "等待", "返回", "重试"} and (
        (start and dy >= 0) or (not start and dy <= 0)
    ):
        return "bottom" if start else "top"
    return None


def is_return_label(label: str) -> bool:
    normalized = str(label or "").strip().lower()
    return any(
        token in normalized
        for token in ("返回", "回退", "重试", "故障排除后", "修复后", "处理后", "retry", "back")
    )


def max_node_height(first_node: dict[str, Any], second_node: dict[str, Any]) -> float:
    return max(
        float(first_node.get("height", 100) or 100),
        float(second_node.get("height", 100) or 100),
    )


def _clamp_unit(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


def build_connector_captions(edge: dict[str, Any]) -> dict[str, Any] | None:
    text = str(edge.get("label", edge.get("text", ""))).strip()
    if not text:
        return None
    text_payload = build_publish_text({**edge, "text": text}, text)
    return {"data": [text_payload]}
