from __future__ import annotations

import json

from app.modules.canvas.schemas import BoardPatchSchema
from app.modules.canvas.schemas import CanvasGenerationRequestSchema


def parse_chat_completion_patch(
    *,
    payload_json: dict[str, object],
    payload: CanvasGenerationRequestSchema,
    provider_config: dict[str, str],
) -> BoardPatchSchema:
    content = extract_message_content(payload_json)
    if not content:
        raise ValueError("AI response did not contain message content")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        error = ValueError(
            f"AI returned invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        )
        error.raw_content = content
        raise error from exc
    normalized = normalize_model_response(payload=payload, parsed=parsed)
    patch = BoardPatchSchema.model_validate(normalized)
    validate_patch_compatibility(patch=patch, payload=payload)
    return patch.model_copy(
        update={
            "generation_info": {
                "source": "ai",
                "provider": provider_config["provider"],
                "model": provider_config["model"],
            }
        }
    )


def extract_message_content(payload_json: dict[str, object]) -> str:
    choices = payload_json.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message", {})
    if not isinstance(message, dict):
        return ""
    content = message.get("content", "")
    return str(content).strip()


def normalize_model_response(
    *,
    payload: CanvasGenerationRequestSchema,
    parsed: dict[str, object],
) -> dict[str, object]:
    if "generation_mode" not in parsed:
        raise ValueError("AI response is missing generation_mode")
    if parsed.get("generation_mode") != payload.generation_mode:
        raise ValueError("AI response generation_mode does not match request")
    return parsed


def validate_patch_compatibility(
    *,
    patch: BoardPatchSchema,
    payload: CanvasGenerationRequestSchema,
) -> None:
    if payload.generation_mode == "targeted_patch" and not patch.operations:
        raise ValueError("targeted_patch response must include at least one operation")
    if payload.generation_mode == "full_board" and patch.full_board is None:
        raise ValueError("full_board response must include full_board")
