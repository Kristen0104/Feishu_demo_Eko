from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.config import Settings
from app.modules.canvas.ai_fallback import build_timeout_fallback_patch
from app.modules.canvas.ai_prompt import build_compact_retry_prompt
from app.modules.canvas.ai_prompt import build_prompt
from app.modules.canvas.ai_prompt import build_system_prompt
from app.modules.canvas.ai_prompt import compact_board_context
from app.modules.canvas.ai_prompt import compact_chat_context
from app.modules.canvas.ai_prompt import compact_edge_context
from app.modules.canvas.ai_prompt import compact_node_context
from app.modules.canvas.ai_prompt import compact_session_metadata
from app.modules.canvas.ai_prompt import compact_source_context
from app.modules.canvas.ai_response import extract_message_content
from app.modules.canvas.ai_response import normalize_model_response
from app.modules.canvas.ai_response import parse_chat_completion_patch
from app.modules.canvas.schemas import BoardPatchSchema
from app.modules.canvas.schemas import CanvasGenerationRequestSchema

logger = logging.getLogger(__name__)


class CanvasAiServiceProtocol(Protocol):
    def generate_patch(
        self,
        *,
        session_id: str,
        payload: CanvasGenerationRequestSchema,
    ) -> BoardPatchSchema: ...


class HttpCanvasAiService:
    def __init__(
        self,
        *,
        settings: Settings,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
            trust_env=False,
        )

    def generate_patch(
        self,
        *,
        session_id: str,
        payload: CanvasGenerationRequestSchema,
    ) -> BoardPatchSchema:
        provider_config = self._resolve_provider_config()
        if provider_config is None:
            raise RuntimeError("Canvas AI provider is not configured")

        request_json = {
            "model": provider_config["model"],
            "temperature": 0.2,
            "max_tokens": int(provider_config["max_tokens"]),
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {
                    "role": "user",
                    "content": self._build_prompt(session_id=session_id, payload=payload),
                },
            ],
        }
        if provider_config["supports_json_object"] == "true":
            request_json["response_format"] = {"type": "json_object"}
        if provider_config["disable_thinking"] == "true":
            request_json["thinking"] = {"type": "disabled"}

        try:
            response = self._post_chat_completion(provider_config, request_json)
        except httpx.ReadTimeout:
            logger.warning("Canvas AI provider timed out; retrying with compact prompt")
            request_json = self._build_compact_retry_request(
                provider_config=provider_config,
                session_id=session_id,
                payload=payload,
            )
            try:
                response = self._post_chat_completion(provider_config, request_json)
            except httpx.ReadTimeout:
                logger.warning("Canvas AI provider timed out again; using local fallback")
                return self._build_timeout_fallback_patch(
                    session_id=session_id,
                    payload=payload,
                    provider_config=provider_config,
                )

        response.raise_for_status()
        try:
            return parse_chat_completion_patch(
                payload_json=response.json(),
                payload=payload,
                provider_config=provider_config,
            )
        except ValueError as exc:
            if not self._is_invalid_model_json(exc):
                raise
            logger.warning("Canvas AI provider returned invalid JSON; retrying compact prompt")
            request_json = self._build_compact_retry_request(
                provider_config=provider_config,
                session_id=session_id,
                payload=payload,
            )
            try:
                retry_response = self._post_chat_completion(provider_config, request_json)
            except httpx.ReadTimeout:
                logger.warning("Canvas AI compact JSON retry timed out; using local fallback")
                return self._build_timeout_fallback_patch(
                    session_id=session_id,
                    payload=payload,
                    provider_config=provider_config,
                    fallback_reason="invalid-json",
                )
            retry_response.raise_for_status()
            try:
                return parse_chat_completion_patch(
                    payload_json=retry_response.json(),
                    payload=payload,
                    provider_config=provider_config,
                )
            except ValueError as retry_exc:
                if not self._is_invalid_model_json(retry_exc):
                    raise
                logger.warning("Canvas AI compact retry returned invalid JSON; using local fallback")
                return self._build_timeout_fallback_patch(
                    session_id=session_id,
                    payload=payload,
                    provider_config=provider_config,
                    fallback_reason="invalid-json",
                )

    @staticmethod
    def _is_invalid_model_json(exc: ValueError) -> bool:
        return isinstance(getattr(exc, "raw_content", None), str)

    def _post_chat_completion(
        self,
        provider_config: dict[str, str],
        request_json: dict[str, object],
    ):
        return self._http_client.post(
            f"{provider_config['api_base'].rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider_config['api_key']}",
                "Content-Type": "application/json",
            },
            json=request_json,
        )

    def _build_compact_retry_request(
        self,
        *,
        provider_config: dict[str, str],
        session_id: str,
        payload: CanvasGenerationRequestSchema,
    ) -> dict[str, object]:
        request_json: dict[str, object] = {
            "model": provider_config["model"],
            "temperature": 0.1,
            "max_tokens": min(int(provider_config["max_tokens"]), 2048),
            "messages": [
                {
                    "role": "system",
                    "content": "只输出一个合法 JSON object，字段遵守 output_contract。",
                },
                {
                    "role": "user",
                    "content": self._build_compact_retry_prompt(
                        session_id=session_id,
                        payload=payload,
                    ),
                },
            ],
        }
        if provider_config["supports_json_object"] == "true":
            request_json["response_format"] = {"type": "json_object"}
        if provider_config["disable_thinking"] == "true":
            request_json["thinking"] = {"type": "disabled"}
        return request_json

    def _resolve_provider_config(self) -> dict[str, str] | None:
        if self._settings.AGENT_API_KEY:
            return {
                "provider": "agent",
                "api_key": self._settings.AGENT_API_KEY,
                "api_base": self._settings.AGENT_API_BASE,
                "model": self._settings.AGENT_MODEL,
                "supports_json_object": "true",
                "disable_thinking": "false",
                "max_tokens": "4096",
            }
        if self._settings.VOLCENGINE_API_KEY:
            return {
                "provider": "volcengine",
                "api_key": self._settings.VOLCENGINE_API_KEY,
                "api_base": self._settings.VOLCENGINE_ENDPOINT,
                "model": self._settings.VOLCENGINE_MODEL,
                "supports_json_object": "false",
                "disable_thinking": "true",
                "max_tokens": "4096",
            }
        return None

    @staticmethod
    def _normalize_model_response(
        *,
        session_id: str,
        payload: CanvasGenerationRequestSchema,
        parsed: dict[str, object],
    ) -> dict[str, object]:
        _ = session_id
        return normalize_model_response(payload=payload, parsed=parsed)

    _build_system_prompt = staticmethod(build_system_prompt)
    _build_prompt = staticmethod(build_prompt)
    _build_compact_retry_prompt = staticmethod(build_compact_retry_prompt)
    _build_timeout_fallback_patch = staticmethod(build_timeout_fallback_patch)
    _extract_message_content = staticmethod(extract_message_content)
    _compact_chat_context = staticmethod(compact_chat_context)
    _compact_board_context = staticmethod(compact_board_context)
    _compact_node_context = staticmethod(compact_node_context)
    _compact_edge_context = staticmethod(compact_edge_context)
    _compact_session_metadata = staticmethod(compact_session_metadata)
    _compact_source_context = staticmethod(compact_source_context)
