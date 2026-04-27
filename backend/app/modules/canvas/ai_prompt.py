from __future__ import annotations

import json
from typing import Any

from app.modules.canvas.schemas import CanvasGenerationRequestSchema


MAX_CHAT_MESSAGES = 4
MAX_CHAT_CONTENT_CHARS = 120
MAX_CONTEXT_NODES = 6
MAX_CONTEXT_EDGES = 8


def build_system_prompt() -> str:
    return "\n".join(
        [
            "你是画板编辑助手，只输出 JSON object，不要 Markdown、解释、额外文本。",
            "根字段仅限：generation_mode, patch_id, summary, operations, style_plan, full_board, targeted_patch。",
            "严禁输出 patches、updateNode、createNode、payload、props、op 等自定义协议字段。",
            "generation_mode/patch_id 必须等于输入；summary 一句中文；operations 必填。",
            "targeted_patch: full_board=null，targeted_patch.operations 与根 operations 相同且非空。",
            "full_board 模式必须提供 full_board(nodes, edges, viewport)，operations 可为空。",
            "节点基础字段：id,type,text,x,y,width,height；可带 style, composite_shape, visual_role, shape_kind, font_size, font_weight, theme_text_color_code, theme_text_background_color_code。",
            "type 只能是 topic、note、text_shape；如需飞书流程图形状，优先使用 visual_role 或 shape_kind，不要自造 type。",
            "边基础字段：id,from,to,type=association；connector_style 可带 label,shape,arrow_style,start_arrow_style,end_arrow_style,style。",
            "所有 id 稳定、可读、不可重复，只含字母、数字、中划线或下划线。",
            "操作仅 node.replace({type,target,content})、node.add({type,target,node})、edge.add({type,target,edge})。",
            "改写选中节点只返回一个 node.replace；拆解结构用 node.replace/node.add/edge.add。",
            "流程图生成具体步骤，避免空泛占位词。",
            "遇到是否/条件/失败/等待/重试/if/else，必须生成 decision 菱形、是/否分支、可返回前面节点。",
            "流程图优先用飞书语义：start/end/decision/data 用 visual_role，常规步骤用 shape_kind=flow_chart_round_rect。",
            "style_plan.template 可选 clean_flow/sunset_flow/forest_flow/mono_exec；样式只用 feishu_board_style_contract。",
            "不要把原始指令原样当节点标题，除非用户要求保留。",
        ]
    )


def build_prompt(
    *,
    session_id: str,
    payload: CanvasGenerationRequestSchema,
) -> str:
    return json.dumps(
        {
            "task": "generate_canvas_patch",
            "session_id": session_id,
            "generation_mode": payload.generation_mode,
            "user_prompt": payload.user_prompt,
            "chat_context": compact_chat_context(payload.chat_context),
            "board_context": compact_board_context(payload.board_context),
            "session_metadata": compact_session_metadata(payload.session_metadata),
            "selection_context": payload.selection_context,
            "feishu_board_style_contract": {
                "node_optional_fields": [
                    "visual_role",
                    "shape_kind",
                    "style",
                    "font_size",
                    "font_weight",
                    "theme_text_color_code",
                    "theme_text_background_color_code",
                ],
                "visual_role_values": ["start", "end", "decision", "data"],
                "shape_kind_values": [
                    "flow_chart_round_rect",
                    "flow_chart_diamond",
                    "flow_chart_parallelogram",
                    "flow_chart_cylinder",
                    "note_shape",
                ],
                "style_fields": [
                    "fill_color",
                    "fill_opacity",
                    "border_style",
                    "border_width",
                    "border_opacity",
                    "border_color",
                    "theme_fill_color_code",
                    "theme_border_color_code",
                ],
                "text_style_fields": [
                    "font_size",
                    "font_weight",
                    "theme_text_color_code",
                    "theme_text_background_color_code",
                ],
                "edge_optional_fields": [
                    "label",
                    "shape",
                    "arrow_style",
                    "start_arrow_style",
                    "end_arrow_style",
                    "style",
                ],
                "edge_shape_values": ["right_angled_polyline", "curve"],
                "arrow_style_values": ["triangle_arrow", "none"],
                "style_guidance": ["style nodes", "3-5 color pairs", "polyline + arrow"],
            },
            "style_plan_contract": {
                "field": "style_plan",
                "available_templates": [
                    "clean_flow",
                    "sunset_flow",
                    "forest_flow",
                    "mono_exec",
                ],
                "usage": "clean general; sunset life; forest health/study; mono work",
            },
            "flow_structure_contract": {
                "decision_node": {
                    "visual_role": "decision",
                    "shape_kind": "flow_chart_diamond",
                    "text": "concrete question",
                },
                "branch_edge_labels": ["是", "否", "通过", "不通过"],
                "loop_edge_labels": ["返回", "重试", "等待"],
                "rules": ["decision has multiple outgoing edges", "loop edge can point back"],
            },
            "output_contract": {
                "generation_mode": payload.generation_mode,
                "patch_id": f"{session_id}-patch-001",
                "summary": "string",
                "style_plan": "optional style plan",
                "operations": [{"type": "node.replace | node.add | edge.add", "target": "string"}],
                "full_board": "full_board mode only",
                "targeted_patch": "targeted_patch mode only",
            },
            "required_output_rules": [
                "Return only one JSON object.",
                "Use the exact output contract; do not invent fields.",
                "targeted_patch.operations must equal operations.",
                "Never return an empty operations array for targeted_patch.",
                "Never use generic placeholders when the user asks for a concrete process.",
            ],
            "examples": {
                "style_examples": {
                    "nodes": [
                        {
                            "id": "flow-start",
                            "type": "topic",
                            "text": "具体起点",
                            "visual_role": "start",
                            "style": {
                                "border_style": "solid",
                                "border_width": "medium",
                            },
                        },
                        {
                            "id": "flow-decision",
                            "type": "note",
                            "text": "具体判断",
                            "visual_role": "decision",
                            "shape_kind": "flow_chart_diamond",
                        },
                    ],
                    "edges": [
                        {
                            "id": "flow-edge-1",
                            "from": "flow-start",
                            "to": "flow-decision",
                            "type": "association",
                            "shape": "right_angled_polyline",
                            "arrow_style": "triangle_arrow",
                        }
                    ],
                }
            },
        },
        ensure_ascii=False,
    )


def build_compact_retry_prompt(
    *,
    session_id: str,
    payload: CanvasGenerationRequestSchema,
) -> str:
    return json.dumps(
        {
            "task": "retry_compact_canvas_patch",
            "generation_mode": payload.generation_mode,
            "user_prompt": payload.user_prompt[:240],
            "selection_context": payload.selection_context,
            "board_context": compact_board_context(payload.board_context),
            "output_contract": {
                "generation_mode": payload.generation_mode,
                "patch_id": f"{session_id}-patch-001",
                "summary": "string",
                "style_plan": "optional {template: clean_flow|sunset_flow|forest_flow|mono_exec}",
                "operations": "targeted_patch must include at least one operation",
                "full_board": "full_board mode returns nodes, edges, viewport",
                "targeted_patch": "targeted_patch mode mirrors operations",
            },
            "style_plan_contract": ["clean_flow", "sunset_flow", "forest_flow", "mono_exec"],
            "rules": [
                "Return only JSON.",
                "Nodes only need id,type,text,x,y,width,height,visual_role,shape_kind.",
                "Edges only need id,from,to,type,label,shape,arrow_style.",
                "Use decision + 是/否/返回 edges when prompt has conditions.",
                "Do not output style; server applies the visual template.",
            ],
        },
        ensure_ascii=False,
    )


def compact_chat_context(chat_context: list[dict[str, str]]) -> list[dict[str, str]]:
    compacted = []
    for message in chat_context[-MAX_CHAT_MESSAGES:]:
        role = str(message.get("role", ""))
        if role not in {"user", "assistant", "system"}:
            continue
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        compacted.append({"role": role, "content": content[:MAX_CHAT_CONTENT_CHARS]})
    return compacted


def compact_board_context(board_context: dict[str, Any]) -> dict[str, Any]:
    nodes = board_context.get("nodes", [])
    edges = board_context.get("edges", [])
    compacted: dict[str, Any] = {
        "node_count": len(nodes) if isinstance(nodes, list) else 0,
        "edge_count": len(edges) if isinstance(edges, list) else 0,
    }
    if isinstance(nodes, list):
        compacted["nodes"] = [
            compact_node_context(node)
            for node in nodes[:MAX_CONTEXT_NODES]
            if isinstance(node, dict)
        ]
    if isinstance(edges, list):
        compacted["edges"] = [
            compact_edge_context(edge)
            for edge in edges[:MAX_CONTEXT_EDGES]
            if isinstance(edge, dict)
        ]
    viewport = board_context.get("viewport")
    if isinstance(viewport, dict):
        compacted["viewport"] = {
            key: viewport[key] for key in ("x", "y", "zoom") if key in viewport
        }
    source = board_context.get("source")
    if isinstance(source, dict):
        compacted["source"] = compact_source_context(source)
    return compacted


def compact_node_context(node: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "id",
        "node_id",
        "type",
        "text",
        "title",
        "x",
        "y",
        "width",
        "height",
        "visual_role",
        "shape_kind",
    )
    return {key: node[key] for key in fields if key in node}


def compact_edge_context(edge: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "id",
        "from",
        "to",
        "type",
        "label",
        "shape",
        "arrow_style",
        "start_arrow_style",
        "end_arrow_style",
    )
    return {key: edge[key] for key in fields if key in edge}


def compact_session_metadata(session_metadata: dict[str, Any]) -> dict[str, Any]:
    source = session_metadata.get("source")
    session = session_metadata.get("session")
    compacted: dict[str, Any] = {}
    if isinstance(source, dict):
        compacted["source"] = compact_source_context(source)
    if isinstance(session, dict):
        compacted["session"] = {
            key: session[key]
            for key in ("mode", "conversation_id", "title")
            if key in session
        }
    return compacted


def compact_source_context(source: dict[str, Any]) -> dict[str, Any]:
    return {
        key: source[key]
        for key in (
            "source_type",
            "document_token",
            "document_id",
            "whiteboard_id",
            "block_id",
            "title",
        )
        if key in source and source[key] not in ("", None)
    }
