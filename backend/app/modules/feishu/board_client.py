from __future__ import annotations

import base64
import json
import math
import random
import time
from pathlib import Path
from collections.abc import Callable
from typing import Any

import httpx

from app.config import Settings, get_settings


class FeishuBoardClient:
    _RATE_LIMIT_RESET_HEADER = "x-ogw-ratelimit-reset"
    _MAX_BACKOFF_SECONDS = 30.0
    _BOARD_READY_RETRIES = 6
    _BOARD_READY_WAIT_SECONDS = 2.0
    _SHAPE_NODE_FIELDS = {"type", "x", "y", "width", "height", "z_index", "composite_shape", "text", "style"}
    _CONNECTOR_FIELDS = {"type", "width", "height", "z_index", "connector", "style"}
    _TEXT_FIELDS = {"text", "font_size", "font_weight", "horizontal_align", "vertical_align"}
    _STYLE_FIELDS = {"fill_color", "fill_opacity", "border_style", "border_color", "border_width", "border_opacity"}
    _CONNECTOR_STYLE_FIELDS = {"border_color", "border_opacity", "border_style", "border_width"}
    _COMPOSITE_SHAPE_FIELDS = {"type"}
    _CONNECTOR_ROOT_FIELDS = {"shape", "start", "end"}
    _CONNECTOR_ENDPOINT_FIELDS = {"arrow_style", "attached_object"}
    _ATTACHED_OBJECT_FIELDS = {"id", "position", "snap_to"}

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._http_client = http_client or httpx.Client(timeout=60, trust_env=False)
        self._tenant_token: str | None = None
        self._tenant_token_expire_at: float = 0
        self._stub_boards: dict[str, dict[str, dict[str, Any]]] = {}
        self._stub_counter = 0

    def import_diagram(
        self,
        whiteboard_id: str,
        *,
        source: str,
        source_type: str = "file",
        syntax: str = "plantuml",
        diagram_type: str = "auto",
        style: str = "board",
        user_access_token: str | None = None,
    ) -> dict[str, Any]:
        content = self._resolve_source_content(source, source_type)
        syntax_type = self._map_syntax_type(syntax)
        style_type = self._map_style_type(style)
        diagram_type_value = self._map_diagram_type(diagram_type)

        fallback_result = {
            "whiteboard_id": whiteboard_id,
            "ticket_id": f"ticket-{whiteboard_id}",
            "syntax": syntax,
            "syntax_type": syntax_type,
            "style": style,
            "style_type": style_type,
            "diagram_type": diagram_type,
            "diagram_type_value": diagram_type_value,
            "source": content,
        }

        if not self._has_credentials():
            return fallback_result

        body = {
            "plant_uml_code": content,
            "syntax_type": syntax_type,
            "style_type": style_type,
            "diagram_type": diagram_type_value,
        }

        result = self._do_with_retry(
            lambda: self._import_diagram_once(
                whiteboard_id,
                body=body,
                user_access_token=user_access_token,
            ),
            max_retries=5,
            max_total_attempts=20,
            retry_on_rate_limit=True,
        )
        if result["error"] is not None:
            raise result["error"]
        ticket_id = result["value"] or f"ticket-{whiteboard_id}"
        return {
            "whiteboard_id": whiteboard_id,
            "ticket_id": ticket_id,
            "syntax": syntax,
            "syntax_type": syntax_type,
            "style": style,
            "style_type": style_type,
            "diagram_type": diagram_type,
            "diagram_type_value": diagram_type_value,
        }

    def _import_diagram_once(
        self,
        whiteboard_id: str,
        *,
        body: dict[str, Any],
        user_access_token: str | None = None,
    ) -> tuple[str, httpx.Headers]:
        payload, headers = self._request_with_headers(
            "POST",
            f"/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes/plantuml",
            json_body=body,
            user_access_token=user_access_token,
        )
        data = payload.get("data", {})
        node_or_ticket = data.get("node_id") or data.get("ticket_id") or f"ticket-{whiteboard_id}"
        return str(node_or_ticket), headers

    def _do_with_retry(
        self,
        fn,
        *,
        max_retries: int,
        max_total_attempts: int,
        retry_on_rate_limit: bool,
        on_retry: Callable[[int, Exception, float], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        if max_total_attempts <= 0:
            max_total_attempts = 20
        failure_count = 0
        rate_limit_hits = 0
        last_error: Exception | None = None
        for attempt in range(max_total_attempts):
            if cancel_check is not None and cancel_check():
                return {
                    "value": None,
                    "error": RuntimeError("重试被取消"),
                    "attempts": attempt,
                    "rate_limit_hits": rate_limit_hits,
                }
            try:
                value, headers = fn()
                return {
                    "value": value,
                    "error": None,
                    "attempts": attempt + 1,
                    "rate_limit_hits": rate_limit_hits,
                }
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                should_retry, is_real_failure = self._classify_error(exc, retry_on_rate_limit=retry_on_rate_limit)
                if self._is_permanent_error(exc):
                    return {
                        "value": None,
                        "error": exc,
                        "attempts": attempt + 1,
                        "rate_limit_hits": rate_limit_hits,
                    }
                is_rate_limit = self._is_rate_limit_error(exc)
                if is_rate_limit:
                    rate_limit_hits += 1
                if not should_retry:
                    return {
                        "value": None,
                        "error": exc,
                        "attempts": attempt + 1,
                        "rate_limit_hits": rate_limit_hits,
                    }
                if is_real_failure:
                    failure_count += 1
                if failure_count > max_retries:
                    return {
                        "value": None,
                        "error": RuntimeError(f"重试 {failure_count} 次后仍失败: {exc}"),
                        "attempts": attempt + 1,
                        "rate_limit_hits": rate_limit_hits,
                    }
                wait = self._get_retry_wait_duration(self._extract_retry_headers(exc), attempt)
                if on_retry is not None:
                    on_retry(attempt + 1, exc, wait)
                if cancel_check is not None and cancel_check():
                    return {
                        "value": None,
                        "error": RuntimeError("重试等待被取消"),
                        "attempts": attempt + 1,
                        "rate_limit_hits": rate_limit_hits,
                    }
                time.sleep(wait)
        return {
            "value": None,
            "error": RuntimeError(f"达到最大总尝试次数 {max_total_attempts}"),
            "attempts": max_total_attempts,
            "rate_limit_hits": rate_limit_hits,
        }

    def create_notes(
        self,
        whiteboard_id: str,
        *,
        nodes_json_or_nodes: str | list[dict[str, Any]],
        source_type: str = "file",
        client_token: str = "",
        user_id_type: str = "open_id",
        user_access_token: str | None = None,
    ) -> dict[str, Any]:
        nodes = self._resolve_nodes(nodes_json_or_nodes, source_type)

        if not self._has_credentials():
            return self._stub_create_notes(
                whiteboard_id,
                nodes=nodes,
            )

        query_parts = [f"user_id_type={user_id_type or 'open_id'}"]
        if client_token:
            query_parts.append(f"client_token={client_token}")
        path = f"/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes?{'&'.join(query_parts)}"
        payload = self._request(
            "POST",
            path,
            json_body={"nodes": nodes},
            user_access_token=user_access_token,
        )
        ids = payload.get("data", {}).get("ids", [])
        return {
            "whiteboard_id": whiteboard_id,
            "node_ids": ids,
            "count": len(ids),
        }

    def get_board_nodes(
        self,
        whiteboard_id: str,
        *,
        user_access_token: str | None = None,
    ) -> dict[str, Any]:
        if not self._has_credentials():
            return {
                "code": 0,
                "msg": "success",
                "data": {
                    "nodes": self._stub_boards.get(whiteboard_id, {}),
                },
            }

        return self._request_with_board_ready_retry(
            lambda: self._request(
                "GET",
                f"/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes",
                user_access_token=user_access_token,
            )
        )

    def get_board_image(
        self,
        whiteboard_id: str,
        *,
        user_access_token: str | None = None,
    ) -> dict[str, Any]:
        if not self._has_credentials():
            return {
                "whiteboard_id": whiteboard_id,
                "preview_url": f"https://stub.preview/{whiteboard_id}.png",
            }

        raw = self._request_raw_with_board_ready_retry(
            lambda: self._request_raw(
                "GET",
                f"/open-apis/board/v1/whiteboards/{whiteboard_id}/download_as_image",
                user_access_token=user_access_token,
            )
        )
        data_url = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
        return {
            "whiteboard_id": whiteboard_id,
            "preview_url": data_url,
        }

    def delete_board_nodes(
        self,
        whiteboard_id: str,
        node_ids: list[str],
        *,
        user_access_token: str | None = None,
    ) -> dict[str, Any]:
        if not node_ids:
            return {
                "whiteboard_id": whiteboard_id,
                "deleted_ids": [],
                "deleted_count": 0,
            }

        if not self._has_credentials():
            board = self._stub_boards.setdefault(whiteboard_id, {})
            deleted = []
            for node_id in node_ids:
                if node_id in board:
                    deleted.append(node_id)
                    del board[node_id]
            return {
                "whiteboard_id": whiteboard_id,
                "deleted_ids": deleted,
                "deleted_count": len(deleted),
            }

        batch_size = 100
        deleted: list[str] = []
        for start in range(0, len(node_ids), batch_size):
            batch = node_ids[start:start + batch_size]
            self._request(
                "DELETE",
                f"/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes/batch_delete",
                json_body={"ids": batch},
                user_access_token=user_access_token,
            )
            deleted.extend(batch)
            if start + batch_size < len(node_ids):
                time.sleep(1)
        return {
            "whiteboard_id": whiteboard_id,
            "deleted_ids": deleted,
            "deleted_count": len(deleted),
        }

    def update_board(
        self,
        whiteboard_id: str,
        *,
        nodes_json_or_nodes: str | list[dict[str, Any]],
        overwrite: bool = False,
        dry_run: bool = False,
        source_type: str = "file",
        user_access_token: str | None = None,
    ) -> dict[str, Any]:
        if dry_run and overwrite:
            existing_ids = self.extract_board_node_ids(
                whiteboard_id,
                user_access_token=user_access_token,
            )
            return {
                "whiteboard_id": whiteboard_id,
                "dry_run": True,
                "existing_count": len(existing_ids),
            }

        old_node_ids: list[str] = []
        if overwrite:
            old_node_ids = self.extract_board_node_ids(
                whiteboard_id,
                user_access_token=user_access_token,
            )

        created = self.create_notes(
            whiteboard_id,
            nodes_json_or_nodes=nodes_json_or_nodes,
            source_type=source_type,
            client_token="",
            user_id_type="open_id",
            user_access_token=user_access_token,
        )

        deleted_count = 0
        if overwrite and old_node_ids:
            new_id_set = set(created["node_ids"])
            to_delete = [node_id for node_id in old_node_ids if node_id not in new_id_set]
            if to_delete:
                try:
                    deleted = self.delete_board_nodes(
                        whiteboard_id,
                        to_delete,
                        user_access_token=user_access_token,
                    )
                except Exception:  # noqa: BLE001
                    deleted_count = 0
                else:
                    deleted_count = deleted["deleted_count"]

        return {
            "whiteboard_id": whiteboard_id,
            "new_node_ids": created["node_ids"],
            "created_count": created["count"],
            "deleted_count": deleted_count,
        }

    def extract_board_node_ids(
        self,
        whiteboard_id: str,
        *,
        user_access_token: str | None = None,
    ) -> list[str]:
        raw = self.get_board_nodes(
            whiteboard_id,
            user_access_token=user_access_token,
        )
        data = raw.get("data", {})
        nodes = data.get("nodes", {})
        if isinstance(nodes, dict):
            return list(nodes.keys())
        if isinstance(nodes, list):
            return [node["id"] for node in nodes if isinstance(node, dict) and node.get("id")]
        return []

    def _stub_create_notes(
        self,
        whiteboard_id: str,
        *,
        nodes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        board = self._stub_boards.setdefault(whiteboard_id, {})
        ids: list[str] = []
        for node in nodes:
            self._stub_counter += 1
            node_id = f"{whiteboard_id}:node:{self._stub_counter}"
            board[node_id] = {
                **node,
                "id": node_id,
            }
            ids.append(node_id)
        return {
            "whiteboard_id": whiteboard_id,
            "node_ids": ids,
            "count": len(ids),
        }

    def resolve_whiteboard_id_from_document(
        self,
        document_id: str,
        *,
        user_access_token: str | None = None,
    ) -> str | None:
        if not self._has_credentials():
            return f"resolved-from-{document_id}"

        token = self._resolve_whiteboard_id_from_root_children(
            document_id,
            user_access_token=user_access_token,
        )
        if token is not None:
            return token

        return self._resolve_whiteboard_id_from_all_blocks(
            document_id,
            user_access_token=user_access_token,
        )

    def _resolve_whiteboard_id_from_root_children(
        self,
        document_id: str,
        *,
        user_access_token: str | None = None,
    ) -> str | None:
        page_token = ""
        for _ in range(1000):
            query = [("page_size", "500"), ("document_revision_id", "-1")]
            if page_token:
                query.append(("page_token", page_token))
            query_string = "&".join(f"{key}={value}" for key, value in query)
            payload = self._request(
                "GET",
                f"/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children?{query_string}",
                user_access_token=user_access_token,
            )
            data = payload.get("data", {})
            items = data.get("items", [])
            if isinstance(items, list):
                token = self._extract_board_token_from_docx_items(items)
                if token is not None:
                    return token
            has_more = bool(data.get("has_more"))
            next_token = data.get("page_token")
            if not has_more or not next_token:
                break
            page_token = str(next_token)
        return None

    def _resolve_whiteboard_id_from_all_blocks(
        self,
        document_id: str,
        *,
        user_access_token: str | None = None,
    ) -> str | None:
        page_token = ""
        for _ in range(1000):
            query = [("page_size", "500")]
            if page_token:
                query.append(("page_token", page_token))
            query_string = "&".join(f"{key}={value}" for key, value in query)
            payload = self._request(
                "GET",
                f"/open-apis/docx/v1/documents/{document_id}/blocks?{query_string}",
                user_access_token=user_access_token,
            )
            data = payload.get("data", {})
            items = data.get("items", [])
            if isinstance(items, list):
                token = self._extract_board_token_from_docx_items(items)
                if token is not None:
                    return token
            has_more = bool(data.get("has_more"))
            next_token = data.get("page_token")
            if not has_more or not next_token:
                break
            page_token = str(next_token)
        return None

    def _resolve_source_content(self, source: str, source_type: str) -> str:
        if source_type == "content":
            return source
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"source file not found: {source}")
        return path.read_text(encoding="utf-8")

    def _resolve_nodes(
        self,
        nodes_json_or_nodes: str | list[dict[str, Any]],
        source_type: str,
    ) -> list[dict[str, Any]]:
        if isinstance(nodes_json_or_nodes, list):
            return nodes_json_or_nodes
        content = self._resolve_source_content(nodes_json_or_nodes, source_type)
        loaded = json.loads(content)
        if not isinstance(loaded, list):
            raise ValueError("nodes_json_or_nodes must resolve to a JSON array")
        return loaded

    def _sanitize_nodes(
        self,
        nodes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        sanitized: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            sanitized_node = self._sanitize_node(node)
            if sanitized_node:
                sanitized.append(sanitized_node)
        return sanitized

    def _sanitize_node(self, node: dict[str, Any]) -> dict[str, Any]:
        node_type = str(node.get("type") or "")
        if node_type == "connector":
            allowed_fields = self._CONNECTOR_FIELDS
        else:
            allowed_fields = self._SHAPE_NODE_FIELDS

        sanitized = {key: node[key] for key in allowed_fields if key in node}
        if node_type == "connector":
            connector = sanitized.get("connector")
            if isinstance(connector, dict):
                sanitized["connector"] = self._sanitize_connector(connector)
            style = sanitized.get("style")
            if isinstance(style, dict):
                sanitized["style"] = {
                    key: style[key]
                    for key in self._CONNECTOR_STYLE_FIELDS
                    if key in style
                }
        else:
            composite_shape = sanitized.get("composite_shape")
            if isinstance(composite_shape, dict):
                sanitized["composite_shape"] = {
                    key: composite_shape[key]
                    for key in self._COMPOSITE_SHAPE_FIELDS
                    if key in composite_shape
                }
            text = sanitized.get("text")
            if isinstance(text, dict):
                sanitized["text"] = {
                    key: text[key]
                    for key in self._TEXT_FIELDS
                    if key in text
                }
            style = sanitized.get("style")
            if isinstance(style, dict):
                sanitized["style"] = {
                    key: style[key]
                    for key in self._STYLE_FIELDS
                    if key in style
                }
        return sanitized

    def _sanitize_connector(self, connector: dict[str, Any]) -> dict[str, Any]:
        sanitized = {key: connector[key] for key in self._CONNECTOR_ROOT_FIELDS if key in connector}
        for endpoint in ("start", "end"):
            endpoint_value = sanitized.get(endpoint)
            if not isinstance(endpoint_value, dict):
                continue
            cleaned_endpoint = {
                key: endpoint_value[key]
                for key in self._CONNECTOR_ENDPOINT_FIELDS
                if key in endpoint_value
            }
            attached_object = cleaned_endpoint.get("attached_object")
            if isinstance(attached_object, dict):
                cleaned_endpoint["attached_object"] = {
                    key: attached_object[key]
                    for key in self._ATTACHED_OBJECT_FIELDS
                    if key in attached_object
                }
            sanitized[endpoint] = cleaned_endpoint
        return sanitized

    def _extract_board_token_from_docx_items(
        self,
        items: list[dict[str, Any]],
    ) -> str | None:
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("block_type") != 43:
                continue
            board = item.get("board")
            if isinstance(board, dict) and board.get("token"):
                return str(board["token"])
        return None

    def _has_credentials(self) -> bool:
        return bool(self._settings.FEISHU_APP_ID and self._settings.FEISHU_APP_SECRET)

    def _map_syntax_type(self, syntax: str) -> int:
        return 2 if syntax.lower() == "mermaid" else 1

    def _map_style_type(self, style: str) -> int:
        return 2 if style.lower() == "classic" else 1

    def _map_diagram_type(self, diagram_type: str) -> int:
        mapping = {
            "auto": 0,
            "mindmap": 1,
            "sequence": 2,
            "activity": 3,
            "class": 4,
            "er": 5,
            "flowchart": 6,
            "state": 7,
            "component": 8,
        }
        return mapping.get(diagram_type.lower(), 0)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        user_access_token: str | None = None,
    ) -> dict[str, Any]:
        payload, _ = self._request_with_headers(
            method,
            path,
            json_body=json_body,
            user_access_token=user_access_token,
        )
        return payload

    def _request_with_headers(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        user_access_token: str | None = None,
    ) -> tuple[dict[str, Any], httpx.Headers]:
        token = user_access_token or self._get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = self._http_client.request(
                method,
                f"https://open.feishu.cn{path}",
                json=json_body,
                headers=headers,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Feishu board request failed: {exc}") from exc
        if response.status_code >= 400:
            error = RuntimeError(f"Feishu board request failed: HTTP {response.status_code}")
            setattr(error, "response_headers", response.headers)
            raise error
        payload = response.json()
        if payload.get("code", 0) != 0:
            error = RuntimeError(
                f"Feishu board request failed: code={payload.get('code')} msg={payload.get('msg')}"
            )
            setattr(error, "response_headers", response.headers)
            raise error
        return payload, response.headers

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        user_access_token: str | None = None,
    ) -> bytes:
        token = user_access_token or self._get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = self._http_client.request(
                method,
                f"https://open.feishu.cn{path}",
                headers=headers,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Feishu board request failed: {exc}") from exc
        if response.status_code >= 400:
            error = RuntimeError(f"Feishu board request failed: HTTP {response.status_code}")
            setattr(error, "response_headers", response.headers)
            raise error
        payload = self._try_parse_json_body(response.content)
        if payload is not None and payload.get("code", 0) != 0:
            error = RuntimeError(
                f"Feishu board request failed: code={payload.get('code')} msg={payload.get('msg')}"
            )
            setattr(error, "response_headers", response.headers)
            raise error
        return response.content

    def _request_with_board_ready_retry(
        self,
        fn: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._BOARD_READY_RETRIES):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not self._is_board_not_ready_error(exc) or attempt == self._BOARD_READY_RETRIES - 1:
                    raise
                time.sleep(self._BOARD_READY_WAIT_SECONDS)
        assert last_error is not None
        raise last_error

    def _request_raw_with_board_ready_retry(
        self,
        fn: Callable[[], bytes],
    ) -> bytes:
        last_error: Exception | None = None
        for attempt in range(self._BOARD_READY_RETRIES):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not self._is_board_not_ready_error(exc) or attempt == self._BOARD_READY_RETRIES - 1:
                    raise
                time.sleep(self._BOARD_READY_WAIT_SECONDS)
        assert last_error is not None
        raise last_error

    def _get_tenant_access_token(self) -> str:
        now = time.time()
        if self._tenant_token and now < self._tenant_token_expire_at:
            return self._tenant_token

        try:
            response = self._http_client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self._settings.FEISHU_APP_ID,
                    "app_secret": self._settings.FEISHU_APP_SECRET,
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to get tenant access token: {exc}") from exc
        if response.status_code >= 400:
            raise RuntimeError(f"Failed to get tenant access token: HTTP {response.status_code}")
        payload = response.json()
        if payload.get("code", 0) != 0:
            raise RuntimeError(
                f"Failed to get tenant access token: code={payload.get('code')} msg={payload.get('msg')}"
            )
        self._tenant_token = payload["tenant_access_token"]
        expire = int(payload.get("expire", 7200))
        self._tenant_token_expire_at = now + max(expire - 60, 60)
        return self._tenant_token

    def _is_rate_limit_error(self, err: Exception) -> bool:
        message = str(err).lower()
        return (
            "429" in message
            or "99991400" in message
            or "frequency limit" in message
            or "rate limit" in message
        )

    def _is_board_not_ready_error(self, err: Exception) -> bool:
        message = str(err).lower()
        return "4003101" in message or "doc data is not ready" in message

    def _try_parse_json_body(self, body: bytes) -> dict[str, Any] | None:
        if not body:
            return None
        stripped = body.lstrip()
        if not stripped.startswith(b"{"):
            return None
        try:
            loaded = json.loads(body.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(loaded, dict):
            return None
        return loaded

    def _is_retryable_error(self, err: Exception) -> bool:
        message = str(err).lower()
        return (
            "500" in message
            or "502" in message
            or "503" in message
            or "429" in message
            or "internal error" in message
            or "rate limit" in message
            or "frequency limit" in message
        )

    def _is_permanent_error(self, err: Exception) -> bool:
        message = str(err).lower()
        return (
            "parse error" in message
            or "invalid request parameter" in message
            or "invalid arg" in message
            or "invalid syntax" in message
        )

    def _classify_error(
        self,
        err: Exception,
        *,
        retry_on_rate_limit: bool,
    ) -> tuple[bool, bool]:
        if self._is_rate_limit_error(err):
            return True, not retry_on_rate_limit
        if self._is_permanent_error(err):
            return False, True
        if self._is_retryable_error(err):
            return True, True
        return False, True

    def _extract_retry_headers(self, err: Exception) -> httpx.Headers | None:
        return getattr(err, "response_headers", None)

    def _get_retry_wait_duration(
        self,
        headers: httpx.Headers | None,
        attempt: int,
    ) -> float:
        if headers is not None:
            for key, value in headers.items():
                if key.lower() == self._RATE_LIMIT_RESET_HEADER:
                    try:
                        reset_seconds = float(value)
                    except ValueError:
                        break
                    jittered = reset_seconds * (0.9 + random.random() * 0.2)
                    return min(jittered, self._MAX_BACKOFF_SECONDS)
        base = min(math.pow(2, float(attempt)), self._MAX_BACKOFF_SECONDS)
        return random.random() * base
