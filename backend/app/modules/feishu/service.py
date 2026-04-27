from __future__ import annotations

import ast
import json

from app.modules.feishu.client import FeishuClient
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
    FeishuBoardPublishResultSchema,
    FeishuBoardSourceSchema,
    FeishuBoardMermaidImportRequestSchema,
    FeishuBoardSyntaxImportResultSchema,
    FeishuBoardSyntaxImportRequestSchema,
    FeishuDocumentWhiteboardNodesSchema,
    FeishuDocumentWhiteboardsDiscoverySchema,
    FeishuDocumentBlocksSchema,
    FeishuDocumentContentSchema,
    FeishuCardSchema,
    FeishuBoardElementMappingSchema,
)


class FeishuService:
    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    def get_card(self, card_id: str) -> FeishuCardSchema:
        return self._client.get_card(card_id)

    def resolve_document_content(
        self,
        share_url: str,
    ) -> FeishuDocumentContentSchema:
        return self._client.resolve_document_content(share_url)

    def resolve_document_share(
        self,
        share_url: str,
    ) -> FeishuDocumentContentSchema:
        return self._client.resolve_document_share(share_url)

    def get_document_blocks(self, document_id: str) -> FeishuDocumentBlocksSchema:
        return self._client.get_document_blocks(document_id)

    def resolve_document_whiteboard_nodes(
        self,
        share_url: str,
    ) -> FeishuDocumentWhiteboardNodesSchema:
        return self._client.resolve_document_whiteboard_nodes(share_url)

    def discover_document_whiteboards(
        self,
        share_url: str,
    ) -> FeishuDocumentWhiteboardsDiscoverySchema:
        document = self._client.resolve_document_content(share_url)
        blocks = self._client.get_document_blocks(document.document_id)
        return FeishuDocumentWhiteboardsDiscoverySchema(
            document_id=document.document_id,
            document_token=document.document_token,
            title=document.title,
            whiteboards=blocks.whiteboards,
        )

    def resolve_document_whiteboard_import_payload(
        self,
        *,
        share_url: str,
        session_id: str,
    ) -> FeishuBoardAdapterPayloadSchema:
        document = self._client.resolve_document_content(share_url)
        whiteboard = self._client.resolve_document_whiteboard_nodes(share_url)
        source_version = (
            f"feishu-doc-blocks:{document.document_id}:{whiteboard.block_id}:{whiteboard.whiteboard_id}"
        )
        normalized_nodes = self._normalize_source_nodes(whiteboard.nodes)
        normalized_edges = self._normalize_source_edges(whiteboard.nodes)
        payload = FeishuBoardAdapterPayloadSchema(
            session_id=session_id,
            source_board=FeishuBoardSourceSchema(
                board_id=whiteboard.whiteboard_id,
                title=document.title,
                nodes=normalized_nodes,
                edges=normalized_edges,
                metadata={
                    "source_type": "feishu_document_whiteboard",
                    "share_url": share_url,
                    "document_id": document.document_id,
                    "document_token": document.document_token,
                    "whiteboard_id": whiteboard.whiteboard_id,
                    "block_id": whiteboard.block_id,
                    "source_version": source_version,
                    "raw_document": document.model_dump(mode="json"),
                    "raw_whiteboard": whiteboard.model_dump(mode="json"),
                },
            ),
            element_mappings=[
                *[
                    FeishuBoardElementMappingSchema(
                        source_element_id=node["id"],
                        working_element_id=node["id"],
                        element_type="node",
                        origin_type="source_import",
                        mapping_status="active",
                        metadata={
                            "source_type": "feishu_document_whiteboard",
                            "document_id": document.document_id,
                            "whiteboard_id": whiteboard.whiteboard_id,
                            "block_id": whiteboard.block_id,
                        },
                    )
                    for node in normalized_nodes
                ],
                *[
                    FeishuBoardElementMappingSchema(
                        source_element_id=edge["id"],
                        working_element_id=edge["id"],
                        element_type="edge",
                        origin_type="source_import",
                        mapping_status="active",
                        metadata={
                            "source_type": "feishu_document_whiteboard",
                            "document_id": document.document_id,
                            "whiteboard_id": whiteboard.whiteboard_id,
                            "block_id": whiteboard.block_id,
                        },
                    )
                    for edge in normalized_edges
                ],
            ],
        )
        return self._client.import_board(payload)

    def import_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> FeishuBoardAdapterPayloadSchema:
        return self._client.import_board(payload)

    def export_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> FeishuBoardAdapterPayloadSchema:
        return self._client.export_board(payload)

    def publish_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> FeishuBoardPublishResultSchema:
        return self._client.publish_board(payload)

    def import_whiteboard_syntax(
        self,
        *,
        whiteboard_id: str,
        payload: FeishuBoardSyntaxImportRequestSchema,
    ) -> FeishuBoardSyntaxImportResultSchema:
        return self._client.import_whiteboard_syntax(
            whiteboard_id=whiteboard_id,
            code=payload.code,
            syntax_type=payload.syntax_type,
            style_type=payload.style_type,
            diagram_type=payload.diagram_type,
        )

    def import_mermaid_whiteboard_syntax(
        self,
        *,
        whiteboard_id: str,
        payload: FeishuBoardMermaidImportRequestSchema,
    ) -> FeishuBoardSyntaxImportResultSchema:
        return self._client.import_whiteboard_syntax(
            whiteboard_id=whiteboard_id,
            code=payload.code,
            syntax_type=payload.syntax_type,
            style_type=payload.style_type,
            diagram_type=payload.diagram_type,
        )

    @staticmethod
    def _normalize_source_nodes(
        nodes: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        normalized_nodes: list[dict[str, object]] = []
        for index, node in enumerate(nodes, start=1):
            if FeishuService._is_connector_node(node):
                continue
            node_id = str(node.get("node_id") or node.get("id") or f"node-{index}").strip()
            if not node_id:
                node_id = f"node-{index}"
            text = FeishuService._extract_node_text(node)
            normalized_node = dict(node)
            normalized_node["id"] = node_id
            normalized_node["text"] = text
            normalized_nodes.append(normalized_node)
        return normalized_nodes

    @staticmethod
    def _normalize_source_edges(
        nodes: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        normalized_edges: list[dict[str, object]] = []
        for index, node in enumerate(nodes, start=1):
            if not FeishuService._is_connector_node(node):
                continue
            connector = node.get("connector")
            if not isinstance(connector, dict):
                continue
            from_node = FeishuService._extract_connector_endpoint(connector, "start")
            to_node = FeishuService._extract_connector_endpoint(connector, "end")
            if not from_node or not to_node:
                continue
            edge_id = str(node.get("id") or node.get("node_id") or f"edge-{index}").strip()
            edge = {
                "id": edge_id or f"edge-{index}",
                "from": from_node,
                "to": to_node,
                "type": "connector",
                "shape": str(connector.get("shape") or "straight"),
            }
            label = FeishuService._extract_connector_caption(connector)
            if label:
                edge["label"] = label
            normalized_edges.append(edge)
        return normalized_edges

    @staticmethod
    def _is_connector_node(node: dict[str, object]) -> bool:
        return str(node.get("type") or "").strip() == "connector"

    @staticmethod
    def _extract_connector_endpoint(connector: dict[str, object], key: str) -> str:
        endpoint = connector.get(key)
        if isinstance(endpoint, dict):
            attached = endpoint.get("attached_object")
            if isinstance(attached, dict):
                attached_id = str(attached.get("id") or "").strip()
                if attached_id:
                    return attached_id
        endpoint_object = connector.get(f"{key}_object")
        if isinstance(endpoint_object, dict):
            object_id = str(endpoint_object.get("id") or "").strip()
            if object_id:
                return object_id
        return ""

    @staticmethod
    def _extract_connector_caption(connector: dict[str, object]) -> str:
        captions = connector.get("captions")
        if isinstance(captions, dict):
            data = captions.get("data")
            if isinstance(data, list):
                return FeishuService._extract_text_from_elements(data)
        return FeishuService._extract_text_payload(captions)

    @staticmethod
    def _extract_node_text(node: dict[str, object]) -> str:
        for key in ("title", "text", "rich_text"):
            text = FeishuService._extract_text_payload(node.get(key))
            if text:
                return text

        return ""

    @staticmethod
    def _extract_text_payload(payload: object) -> str:
        if isinstance(payload, str):
            stripped = payload.strip()
            parsed = FeishuService._parse_text_payload_string(stripped)
            if parsed is not None:
                parsed_text = FeishuService._extract_text_payload(parsed)
                if parsed_text:
                    return parsed_text
            return stripped
        if isinstance(payload, dict):
            for key in ("text", "plain_text", "content", "title"):
                if key not in payload:
                    continue
                value = payload.get(key)
                if isinstance(value, list):
                    text = FeishuService._extract_text_from_elements(value)
                else:
                    text = FeishuService._extract_text_payload(value)
                if text:
                    return text
            if isinstance(payload.get("elements"), list):
                return FeishuService._extract_text_from_elements(payload["elements"])
        if isinstance(payload, list):
            return FeishuService._extract_text_from_elements(payload)
        return ""

    @staticmethod
    def _parse_text_payload_string(payload: str) -> object | None:
        if not payload or payload[0] not in ("{", "["):
            return None
        for parser in (json.loads, ast.literal_eval):
            try:
                return parser(payload)
            except (SyntaxError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return None

    @staticmethod
    def _extract_text_from_elements(elements: list[object]) -> str:
        parts: list[str] = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            text_run = element.get("text_run")
            if isinstance(text_run, dict):
                content = text_run.get("content")
                if isinstance(content, str) and content:
                    parts.append(content)
                    continue
            text_value = element.get("text")
            text = FeishuService._extract_text_payload(text_value)
            if text:
                parts.append(text)
                continue
            content_value = element.get("content")
            if isinstance(content_value, list):
                content = FeishuService._extract_text_from_elements(content_value)
                if content:
                    parts.append(content)
        return "".join(parts).strip()
