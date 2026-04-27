from __future__ import annotations

from app.modules.canvas.schemas import BoardPatchSchema
from app.modules.canvas.schemas import CanvasGenerationRequestSchema


def build_timeout_fallback_patch(
    *,
    session_id: str,
    payload: CanvasGenerationRequestSchema,
    provider_config: dict[str, str],
    fallback_reason: str = "timeout",
) -> BoardPatchSchema:
    patch_id = f"{session_id}-{fallback_reason}-fallback"
    if payload.generation_mode == "targeted_patch":
        return _build_targeted_timeout_fallback(
            patch_id=patch_id,
            payload=payload,
            provider_config=provider_config,
            fallback_reason=fallback_reason,
        )
    return _build_full_board_timeout_fallback(
        patch_id=patch_id,
        payload=payload,
        provider_config=provider_config,
        fallback_reason=fallback_reason,
    )


def _build_targeted_timeout_fallback(
    *,
    patch_id: str,
    payload: CanvasGenerationRequestSchema,
    provider_config: dict[str, str],
    fallback_reason: str,
) -> BoardPatchSchema:
    selected_ids = []
    if isinstance(payload.selection_context, dict):
        selected_ids = [
            str(node_id)
            for node_id in payload.selection_context.get("selectedNodeIds", [])
            if str(node_id).strip()
        ]
    target = selected_ids[0] if selected_ids else "node-1"
    operation = {
        "type": "node.replace",
        "target": target,
        "content": f"根据指令更新：{payload.user_prompt[:80]}",
    }
    return BoardPatchSchema(
        generation_mode="targeted_patch",
        patch_id=patch_id,
        operations=[operation],
        summary=_fallback_summary(fallback_reason, "修改"),
        full_board=None,
        targeted_patch={
            "selection": {"selectedNodeIds": selected_ids},
            "operations": [operation],
        },
        generation_info=_fallback_generation_info(provider_config, fallback_reason),
    )


def _build_full_board_timeout_fallback(
    *,
    patch_id: str,
    payload: CanvasGenerationRequestSchema,
    provider_config: dict[str, str],
    fallback_reason: str,
) -> BoardPatchSchema:
    topic = payload.user_prompt.strip() or "流程"
    nodes = [
        {
            "id": "fallback-start",
            "type": "topic",
            "text": f"开始{topic[:18]}",
            "x": 120,
            "y": 180,
            "width": 220,
            "height": 100,
        },
        {
            "id": "fallback-prepare",
            "type": "note",
            "text": "准备必要信息和材料",
            "x": 440,
            "y": 180,
            "width": 260,
            "height": 110,
        },
        {
            "id": "fallback-action",
            "type": "note",
            "text": "按步骤执行核心动作",
            "x": 800,
            "y": 180,
            "width": 260,
            "height": 110,
        },
        {
            "id": "fallback-check",
            "type": "note",
            "text": "是否完成目标?",
            "x": 1160,
            "y": 150,
            "width": 240,
            "height": 160,
            "shape_kind": "flow_chart_diamond",
        },
        {
            "id": "fallback-end",
            "type": "topic",
            "text": f"{topic[:18]}结束",
            "x": 1520,
            "y": 180,
            "width": 220,
            "height": 100,
        },
    ]
    edges = [
        {
            "id": "fallback-edge-1",
            "from": "fallback-start",
            "to": "fallback-prepare",
            "type": "association",
        },
        {
            "id": "fallback-edge-2",
            "from": "fallback-prepare",
            "to": "fallback-action",
            "type": "association",
        },
        {
            "id": "fallback-edge-3",
            "from": "fallback-action",
            "to": "fallback-check",
            "type": "association",
        },
        {
            "id": "fallback-edge-4",
            "from": "fallback-check",
            "to": "fallback-end",
            "type": "association",
            "label": "是",
        },
    ]
    return BoardPatchSchema(
        generation_mode="full_board",
        patch_id=patch_id,
        operations=[],
        summary=_fallback_summary(fallback_reason, "流程图"),
        full_board={"nodes": nodes, "edges": edges, "viewport": {"x": 0, "y": 0, "zoom": 1}},
        targeted_patch=None,
        generation_info=_fallback_generation_info(provider_config, fallback_reason),
    )


def _fallback_generation_info(
    provider_config: dict[str, str],
    fallback_reason: str,
) -> dict[str, str]:
    return {
        "source": "ai",
        "provider": f"{provider_config['provider']}-{fallback_reason}-fallback",
        "model": provider_config["model"],
    }


def _fallback_summary(fallback_reason: str, target: str) -> str:
    if fallback_reason == "invalid-json":
        return f"模型输出 JSON 不完整，已生成本地降级{target}"
    return f"模型超时，已生成本地降级{target}"
