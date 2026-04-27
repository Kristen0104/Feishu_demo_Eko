from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException

from app.modules.feishu.publisher import build_publish_nodes
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
    FeishuBoardElementMappingSchema,
    FeishuBoardPublishResultSchema,
    FeishuBoardSourceSchema,
    FeishuBoardSyntaxImportResultSchema,
    FeishuBoardWorkingSchema,
    FeishuCardSchema,
    FeishuDocumentBlockSchema,
    FeishuDocumentBlocksSchema,
    FeishuDocumentContentSchema,
    FeishuDocumentWhiteboardSchema,
    FeishuDocumentWhiteboardNodesSchema,
    FeishuWhiteboardNodesSchema,
)


class FeishuHttpClientProtocol(Protocol):
    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        ...

    def post(
        self,
        url: str,
        json: dict[str, Any],
        timeout: int,
        headers: dict[str, str] | None = None,
    ) -> Any:
        ...

    def get(
        self,
        url: str,
        headers: dict[str, str],
        timeout: int,
    ) -> Any:
        ...


class FeishuUpstreamError(HTTPException):
    def __init__(
        self,
        *,
        message: str,
        url: str,
        upstream_status: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        detail: dict[str, Any] = {
            "message": message,
            "url": url,
        }
        if upstream_status is not None:
            detail["upstream_status"] = upstream_status
        if payload:
            feishu_code = payload.get("code")
            if feishu_code not in (None, ""):
                detail["feishu_code"] = feishu_code
            feishu_message = payload.get("msg", payload.get("message", ""))
            if feishu_message:
                detail["feishu_message"] = str(feishu_message)
        super().__init__(status_code=502, detail=detail)


class HttpxFeishuHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client
        self._timeout_seconds = timeout_seconds

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def post(
        self,
        url: str,
        json: dict[str, Any],
        timeout: int,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        if self._client is not None:
            return self._client.post(url, json=json, headers=headers, timeout=timeout)
        return httpx.post(url, json=json, headers=headers, timeout=timeout)

    def get(
        self,
        url: str,
        headers: dict[str, str],
        timeout: int,
    ) -> httpx.Response:
        if self._client is not None:
            return self._client.get(url, headers=headers, timeout=timeout)
        return httpx.get(url, headers=headers, timeout=timeout)

    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self.get(
            url,
            headers=headers or {},
            timeout=int(self._timeout_seconds),
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise FeishuUpstreamError(
                message="Feishu upstream returned invalid JSON",
                url=url,
                upstream_status=response.status_code,
            ) from exc
        if not isinstance(payload, dict):
            raise FeishuUpstreamError(
                message="Feishu upstream returned a non-object payload",
                url=url,
                upstream_status=response.status_code,
            )
        return {
            "__http_status_code__": response.status_code,
            "__payload__": payload,
        }


class FeishuClient:
    def __init__(
        self,
        *,
        http_client: FeishuHttpClientProtocol | None = None,
        app_id: str = "",
        app_secret: str = "",
        document_endpoint_template: str = (
            "https://open.feishu.cn/open-apis/docx/v1/documents/{document_token}"
        ),
        raw_content_endpoint_template: str = (
            "https://open.feishu.cn/open-apis/docx/v1/documents/{document_token}/raw_content"
        ),
        document_blocks_endpoint_template: str = (
            "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks"
        ),
        whiteboard_nodes_endpoint_template: str = (
            "https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes"
        ),
        whiteboard_publish_endpoint_template: str = "",
        whiteboard_theme_update_endpoint_template: str = (
            "https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/update_theme"
        ),
        whiteboard_syntax_import_endpoint_template: str = (
            "https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes/plantuml"
        ),
        access_token_provider: Callable[[], str] | None = None,
    ) -> None:
        self._http_client = http_client
        self._app_id = app_id
        self._app_secret = app_secret
        self._document_endpoint_template = document_endpoint_template
        self._raw_content_endpoint_template = raw_content_endpoint_template
        self._document_blocks_endpoint_template = document_blocks_endpoint_template
        self._whiteboard_nodes_endpoint_template = whiteboard_nodes_endpoint_template
        self._whiteboard_publish_endpoint_template = whiteboard_publish_endpoint_template
        self._whiteboard_theme_update_endpoint_template = (
            whiteboard_theme_update_endpoint_template
        )
        self._whiteboard_syntax_import_endpoint_template = (
            whiteboard_syntax_import_endpoint_template
        )
        self._access_token_provider = access_token_provider
        self._cached_access_token: str | None = None

    def get_card(self, card_id: str) -> FeishuCardSchema:
        return FeishuCardSchema(
            card_id=card_id,
            title="Stub Feishu Card",
            platform="feishu",
        )

    @staticmethod
    def extract_document_token(share_url: str) -> str:
        parsed = urlparse(share_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        for marker in ("docx", "docs"):
            if marker in path_parts:
                marker_index = path_parts.index(marker)
                if marker_index + 1 < len(path_parts):
                    token = path_parts[marker_index + 1].strip()
                    if token:
                        return token
        if path_parts:
            token = path_parts[-1].strip()
            if token:
                return token
        raise ValueError(f"Unable to parse document token from share_url: {share_url}")

    def resolve_document_share(self, share_url: str) -> FeishuDocumentContentSchema:
        return self.resolve_document_content(share_url)

    def resolve_document_content(self, share_url: str) -> FeishuDocumentContentSchema:
        document_token = self.extract_document_token(share_url)
        if self._http_client is None:
            return FeishuDocumentContentSchema(
                document_token=document_token,
                document_id=document_token,
                title="Stub Feishu Document",
                plain_text="",
                raw_content={
                    "document_token": document_token,
                    "document_id": document_token,
                    "share_url": share_url,
                },
                share_url=share_url,
            )

        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}

        metadata_url = self._document_endpoint_template.format(
            document_token=document_token,
            share_url=share_url,
        )
        raw_content_url = self._raw_content_endpoint_template.format(
            document_token=document_token,
            share_url=share_url,
        )

        metadata_payload = self._http_get_json(metadata_url, headers=headers)
        raw_content_payload = self._http_get_json(raw_content_url, headers=headers)

        normalized_metadata = self._normalize_document_payload(metadata_payload)
        normalized_raw_content = self._normalize_document_payload(raw_content_payload)

        title = str(
            normalized_metadata.get(
                "title",
                normalized_raw_content.get("title", "Untitled Feishu Document"),
            )
        )
        plain_text = str(
            normalized_raw_content.get(
                "content",
                normalized_raw_content.get(
                    "plain_text",
                    normalized_metadata.get("plain_text", ""),
                ),
            )
        )
        raw_content = normalized_raw_content.get("raw_content", normalized_raw_content)
        if not isinstance(raw_content, dict):
            raw_content = {"value": raw_content}

        return FeishuDocumentContentSchema(
            document_token=document_token,
            document_id=document_token,
            title=title,
            plain_text=plain_text,
            raw_content=raw_content,
            share_url=share_url,
        )

    def get_document_blocks(self, document_id: str) -> FeishuDocumentBlocksSchema:
        if self._http_client is None:
            return FeishuDocumentBlocksSchema(document_id=document_id)

        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
        next_page_token = ""
        seen_page_tokens: set[str] = set()
        blocks: list[FeishuDocumentBlockSchema] = []
        whiteboards: list[FeishuDocumentWhiteboardSchema] = []

        while True:
            request_page_token = next_page_token
            blocks_url = self._build_document_blocks_url(
                document_id=document_id,
                page_token=request_page_token,
            )
            payload = self._http_get_json(blocks_url, headers=headers)
            normalized_payload = self._normalize_blocks_payload(payload)

            for item in normalized_payload.get("items", []):
                normalized_block = self._normalize_block_item(item)
                if normalized_block is None:
                    continue
                blocks.append(normalized_block)
                whiteboard = self._extract_whiteboard(normalized_block)
                if whiteboard is not None:
                    whiteboards.append(whiteboard)

            has_more = bool(normalized_payload.get("has_more", False))
            next_page_token = str(normalized_payload.get("page_token", "")).strip()
            if not has_more:
                break
            if not next_page_token:
                raise FeishuUpstreamError(
                    message="Feishu document blocks pagination did not return a next page token",
                    url=blocks_url,
                )
            if next_page_token == request_page_token or next_page_token in seen_page_tokens:
                raise FeishuUpstreamError(
                    message="Feishu document blocks pagination page_token did not advance",
                    url=blocks_url,
                )
            seen_page_tokens.add(next_page_token)

        return FeishuDocumentBlocksSchema(
            document_id=document_id,
            blocks=blocks,
            whiteboards=whiteboards,
        )

    def get_whiteboard_nodes(self, whiteboard_id: str) -> FeishuWhiteboardNodesSchema:
        if self._http_client is None:
            return FeishuWhiteboardNodesSchema(whiteboard_id=whiteboard_id)

        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
        url = self._whiteboard_nodes_endpoint_template.format(
            whiteboard_id=whiteboard_id,
            board_id=whiteboard_id,
        )
        payload = self._http_get_json(url, headers=headers)
        normalized_payload = self._normalize_whiteboard_nodes_payload(payload)
        return FeishuWhiteboardNodesSchema(
            whiteboard_id=whiteboard_id,
            nodes=normalized_payload["nodes"],
            raw_payload=normalized_payload["raw_payload"],
        )

    def resolve_document_whiteboard_nodes(
        self,
        share_url: str,
    ) -> FeishuDocumentWhiteboardNodesSchema:
        document = self.resolve_document_content(share_url)
        blocks = self.get_document_blocks(document.document_id)
        first_whiteboard = next(iter(blocks.whiteboards), None)
        if first_whiteboard is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "No whiteboard discovered in Feishu document blocks",
                    "document_id": document.document_id,
                },
            )
        whiteboard_nodes = self.get_whiteboard_nodes(first_whiteboard.whiteboard_id)
        return FeishuDocumentWhiteboardNodesSchema(
            document_id=document.document_id,
            whiteboard_id=first_whiteboard.whiteboard_id,
            block_id=first_whiteboard.block_id,
            nodes=whiteboard_nodes.nodes,
            raw_payload=whiteboard_nodes.raw_payload,
        )

    def import_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> FeishuBoardAdapterPayloadSchema:
        return FeishuBoardAdapterPayloadSchema(
            session_id=payload.session_id,
            source_board=payload.source_board,
            working_board=payload.working_board
            or self._build_working_board(payload),
            element_mappings=payload.element_mappings
            or self._build_identity_mappings(payload),
        )

    def export_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> FeishuBoardAdapterPayloadSchema:
        working_board = payload.working_board or self._build_working_board(payload)
        return FeishuBoardAdapterPayloadSchema(
            session_id=payload.session_id,
            source_board=self._build_source_board(working_board, payload.source_board),
            working_board=working_board,
            element_mappings=payload.element_mappings
            or self._build_identity_mappings(payload, working_board),
        )

    def publish_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> FeishuBoardPublishResultSchema:
        exported_board = self.export_board(payload)
        board_id = exported_board.source_board.board_id
        if not self._whiteboard_publish_endpoint_template or self._http_client is None:
            return FeishuBoardPublishResultSchema(
                mode="adapter_only",
                accepted=True,
                session_id=exported_board.session_id,
                board_id=board_id,
                exported_board=exported_board,
            )

        access_token = self._get_access_token()
        if not access_token:
            return FeishuBoardPublishResultSchema(
                mode="adapter_only",
                accepted=True,
                session_id=exported_board.session_id,
                board_id=board_id,
                exported_board=exported_board,
                upstream_payload={
                    "reason": "missing_access_token",
                },
            )

        existing_nodes = self.get_whiteboard_nodes(board_id)
        if existing_nodes.nodes:
            return FeishuBoardPublishResultSchema(
                mode="upstream",
                accepted=False,
                session_id=exported_board.session_id,
                board_id=board_id,
                exported_board=exported_board,
                upstream_payload={
                    "reason": "target_board_not_empty",
                    "existing_node_count": len(existing_nodes.nodes),
                },
            )

        headers = (
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            if access_token
            else {"Content-Type": "application/json; charset=utf-8"}
        )
        url = self._whiteboard_publish_endpoint_template.format(
            whiteboard_id=board_id,
            board_id=board_id,
        )
        publish_nodes = build_publish_nodes(exported_board)
        response = self._http_client.post(
            url,
            json={"nodes": publish_nodes},
            headers=headers,
            timeout=10,
        )
        upstream_payload = {
            "create_nodes": self._json_from_response(response, url=url),
        }
        theme_name = str(exported_board.source_board.metadata.get("theme", "")).strip()
        if theme_name:
            theme_url = self._whiteboard_theme_update_endpoint_template.format(
                whiteboard_id=board_id,
                board_id=board_id,
            )
            theme_response = self._http_client.post(
                theme_url,
                json={"theme": theme_name},
                headers=headers,
                timeout=10,
            )
            upstream_payload["update_theme"] = self._json_from_response(
                theme_response,
                url=theme_url,
            )
        return FeishuBoardPublishResultSchema(
            mode="upstream",
            accepted=True,
            session_id=exported_board.session_id,
            board_id=board_id,
            exported_board=exported_board,
            upstream_payload=upstream_payload,
        )

    def import_whiteboard_syntax(
        self,
        *,
        whiteboard_id: str,
        code: str,
        syntax_type: int,
        style_type: int = 1,
        diagram_type: int = 0,
    ) -> FeishuBoardSyntaxImportResultSchema:
        if not self._whiteboard_syntax_import_endpoint_template or self._http_client is None:
            return FeishuBoardSyntaxImportResultSchema(
                mode="adapter_only",
                accepted=True,
                board_id=whiteboard_id,
                upstream_payload={
                    "reason": "missing_syntax_import_endpoint",
                },
            )

        access_token = self._get_access_token()
        if not access_token:
            return FeishuBoardSyntaxImportResultSchema(
                mode="adapter_only",
                accepted=True,
                board_id=whiteboard_id,
                upstream_payload={
                    "reason": "missing_access_token",
                },
            )

        url = self._whiteboard_syntax_import_endpoint_template.format(
            whiteboard_id=whiteboard_id,
            board_id=whiteboard_id,
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        request_payload = {
            "plant_uml_code": code,
            "style_type": int(style_type),
            "syntax_type": int(syntax_type),
            "diagram_type": int(diagram_type),
        }
        response = self._http_client.post(
            url,
            json=request_payload,
            headers=headers,
            timeout=10,
        )
        return FeishuBoardSyntaxImportResultSchema(
            mode="upstream",
            accepted=True,
            board_id=whiteboard_id,
            upstream_payload={
                "syntax_import": self._json_from_response(response, url=url),
            },
        )

    def _get_access_token(self) -> str:
        if self._access_token_provider is not None:
            return self._access_token_provider()
        if self._cached_access_token is not None:
            return self._cached_access_token
        if not self._app_id or not self._app_secret:
            return ""
        if self._http_client is None:
            return ""

        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        response = self._http_client.post(
            token_url,
            json={
                "app_id": self._app_id,
                "app_secret": self._app_secret,
            },
            timeout=10,
        )
        payload = self._json_from_response(response, url=token_url)
        token = str(
            payload.get(
                "tenant_access_token",
                payload.get("tenant_access_token_value", ""),
            )
        )
        self._cached_access_token = token
        return token

    def _http_get_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        if hasattr(self._http_client, "get_json"):
            return self._json_from_response(
                self._http_client.get_json(url, headers=headers or None),
                url=url,
            )
        response = self._http_client.get(url, headers=headers, timeout=10)
        return self._json_from_response(response, url=url)

    @staticmethod
    def _json_from_response(response: Any, *, url: str) -> dict[str, Any]:
        if isinstance(response, dict) and "__payload__" in response:
            payload = response.get("__payload__")
            status_code = int(response.get("__http_status_code__", 200))
            if not isinstance(payload, dict):
                raise FeishuUpstreamError(
                    message="Feishu upstream returned a non-object payload",
                    url=url,
                    upstream_status=status_code,
                )
            if status_code >= 400:
                raise FeishuUpstreamError(
                    message="Feishu upstream request failed",
                    url=url,
                    upstream_status=status_code,
                    payload=payload,
                )
            return FeishuClient._normalize_feishu_payload(
                payload,
                url=url,
                status_code=status_code,
            )
        if hasattr(response, "json"):
            status_code = int(getattr(response, "status_code", 200))
            try:
                payload = response.json()
            except ValueError as exc:
                raise FeishuUpstreamError(
                    message="Feishu upstream returned invalid JSON",
                    url=url,
                    upstream_status=status_code,
                ) from exc
            if isinstance(payload, dict):
                if status_code >= 400:
                    raise FeishuUpstreamError(
                        message="Feishu upstream request failed",
                        url=url,
                        upstream_status=status_code,
                        payload=payload,
                    )
                return FeishuClient._normalize_feishu_payload(
                    payload,
                    url=url,
                    status_code=status_code,
                )
        if isinstance(response, dict):
            return FeishuClient._normalize_feishu_payload(
                response,
                url=url,
                status_code=200,
            )
        raise FeishuUpstreamError(
            message="Feishu upstream returned an invalid response",
            url=url,
        )

    @staticmethod
    def _normalize_feishu_payload(
        payload: dict[str, Any],
        *,
        url: str,
        status_code: int,
    ) -> dict[str, Any]:
        feishu_code = payload.get("code")
        if feishu_code not in (None, 0, "0"):
            raise FeishuUpstreamError(
                message="Feishu upstream returned an error payload",
                url=url,
                upstream_status=status_code,
                payload=payload,
            )
        if "data" in payload and isinstance(payload["data"], dict):
            return payload["data"]
        return payload

    @staticmethod
    def _normalize_document_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if "data" in payload and isinstance(payload["data"], dict):
            payload = payload["data"]
        if "document" in payload and isinstance(payload["document"], dict):
            payload = {**payload, **payload["document"]}
        return payload

    def _build_document_blocks_url(self, *, document_id: str, page_token: str) -> str:
        base_url = self._document_blocks_endpoint_template.format(
            document_id=document_id,
            document_token=document_id,
        )
        if not page_token:
            return base_url
        return f"{base_url}?{urlencode({'page_token': page_token})}"

    @staticmethod
    def _normalize_blocks_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if "data" in payload and isinstance(payload["data"], dict):
            payload = payload["data"]
        return payload

    @staticmethod
    def _normalize_whiteboard_nodes_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if "data" in payload and isinstance(payload["data"], dict):
            payload = payload["data"]
        items = payload.get("items", payload.get("nodes", []))
        if not isinstance(items, list):
            items = []
        normalized_nodes = [item for item in items if isinstance(item, dict)]
        return {
            "nodes": normalized_nodes,
            "raw_payload": payload if isinstance(payload, dict) else {},
        }

    @staticmethod
    def _normalize_block_item(item: Any) -> FeishuDocumentBlockSchema | None:
        if not isinstance(item, dict):
            return None
        block_payload = item.get("block")
        raw_block = block_payload if isinstance(block_payload, dict) else item
        block_id = str(raw_block.get("block_id", item.get("block_id", ""))).strip()
        if not block_id:
            return None

        block_type_value = raw_block.get("block_type", item.get("block_type", 0))
        try:
            block_type = int(block_type_value)
        except (TypeError, ValueError):
            block_type = 0

        return FeishuDocumentBlockSchema(
            block_id=block_id,
            block_type=block_type,
            raw_block=raw_block,
        )

    @staticmethod
    def _extract_whiteboard(
        block: FeishuDocumentBlockSchema,
    ) -> FeishuDocumentWhiteboardSchema | None:
        if block.block_type != 43:
            return None
        board = block.raw_block.get("board")
        if not isinstance(board, dict):
            return None
        whiteboard_id = str(board.get("token", "")).strip()
        if not whiteboard_id:
            return None
        return FeishuDocumentWhiteboardSchema(
            whiteboard_id=whiteboard_id,
            block_id=block.block_id,
        )

    def _build_working_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> FeishuBoardWorkingSchema:
        snapshot = {
            "nodes": list(payload.source_board.nodes),
            "edges": list(payload.source_board.edges),
        }
        return FeishuBoardWorkingSchema(
            working_board_id=f"{payload.source_board.board_id}-working",
            session_id=payload.session_id,
            latest_version=1,
            crdt_document=snapshot,
            latest_snapshot=snapshot,
            offline_state="clean",
        )

    def _build_identity_mappings(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
        working_board: FeishuBoardWorkingSchema | None = None,
    ) -> list[FeishuBoardElementMappingSchema]:
        mappings: list[FeishuBoardElementMappingSchema] = []
        for node in payload.source_board.nodes:
            node_id = node.get("id", "")
            mappings.append(
                FeishuBoardElementMappingSchema(
                    source_element_id=node_id,
                    working_element_id=node_id,
                    element_type="node",
                )
            )
        for edge in payload.source_board.edges:
            edge_id = edge.get("id", "")
            mappings.append(
                FeishuBoardElementMappingSchema(
                    source_element_id=edge_id,
                    working_element_id=edge_id,
                    element_type="edge",
                )
            )
        if working_board is not None and not mappings:
            return []
        return mappings

    def _build_source_board(
        self,
        working_board: FeishuBoardWorkingSchema,
        source_board: FeishuBoardSourceSchema,
    ) -> FeishuBoardSourceSchema:
        snapshot = working_board.latest_snapshot
        return FeishuBoardSourceSchema(
            board_id=source_board.board_id,
            title=source_board.title,
            nodes=list(snapshot.get("nodes", [])),
            edges=list(snapshot.get("edges", [])),
            metadata=dict(source_board.metadata),
        )
