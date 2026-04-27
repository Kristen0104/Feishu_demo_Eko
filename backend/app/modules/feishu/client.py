from __future__ import annotations

from app.modules.feishu.board_client import FeishuBoardClient
from app.modules.feishu.schemas import (
    FeishuBoardCreateNotesRequest,
    FeishuBoardCreateNotesSchema,
    FeishuBoardDeleteRequest,
    FeishuBoardDeleteSchema,
    FeishuBoardImageSchema,
    FeishuBoardImportRequest,
    FeishuBoardImportSchema,
    FeishuBoardNodesSchema,
    FeishuBoardUpdateRequest,
    FeishuBoardUpdateSchema,
    FeishuCardSchema,
)


class FeishuClient:
    def __init__(self, board_client: FeishuBoardClient | None = None) -> None:
        self._board_client = board_client or FeishuBoardClient()

    # Platform API wiring will live here once the module stops being a stub.
    def get_card(self, card_id: str) -> FeishuCardSchema:
        return FeishuCardSchema(
            card_id=card_id,
            title="Stub Feishu Card",
            platform="feishu",
        )

    def import_diagram(self, payload: FeishuBoardImportRequest) -> FeishuBoardImportSchema:
        result = self._board_client.import_diagram(
            payload.whiteboard_id,
            source=payload.source,
            source_type=payload.source_type,
            syntax=payload.syntax,
            diagram_type=payload.diagram_type,
            style=payload.style,
            user_access_token=payload.user_access_token,
        )
        return FeishuBoardImportSchema(**result)

    def create_notes(self, payload: FeishuBoardCreateNotesRequest) -> FeishuBoardCreateNotesSchema:
        result = self._board_client.create_notes(
            payload.whiteboard_id,
            nodes_json_or_nodes=payload.nodes if payload.nodes is not None else (payload.nodes_json or "[]"),
            source_type=payload.source_type,
            client_token=payload.client_token,
            user_id_type=payload.user_id_type,
            user_access_token=payload.user_access_token,
        )
        return FeishuBoardCreateNotesSchema(**result)

    def get_board_nodes(self, whiteboard_id: str, user_access_token: str | None = None) -> FeishuBoardNodesSchema:
        result = self._board_client.get_board_nodes(whiteboard_id, user_access_token=user_access_token)
        return FeishuBoardNodesSchema(nodes=result["data"]["nodes"])

    def get_board_image(self, whiteboard_id: str, user_access_token: str | None = None) -> FeishuBoardImageSchema:
        result = self._board_client.get_board_image(whiteboard_id, user_access_token=user_access_token)
        return FeishuBoardImageSchema(**result)

    def update_board(self, payload: FeishuBoardUpdateRequest) -> FeishuBoardUpdateSchema:
        result = self._board_client.update_board(
            payload.whiteboard_id,
            nodes_json_or_nodes=payload.nodes if payload.nodes is not None else (payload.nodes_json or "[]"),
            source_type=payload.source_type,
            overwrite=payload.overwrite,
            dry_run=payload.dry_run,
            user_access_token=payload.user_access_token,
        )
        return FeishuBoardUpdateSchema(**result)

    def delete_board(self, payload: FeishuBoardDeleteRequest) -> FeishuBoardDeleteSchema:
        node_ids = payload.node_ids
        if payload.all:
            node_ids = self._board_client.extract_board_node_ids(
                payload.whiteboard_id,
                user_access_token=payload.user_access_token,
            )
        result = self._board_client.delete_board_nodes(
            payload.whiteboard_id,
            node_ids,
            user_access_token=payload.user_access_token,
        )
        return FeishuBoardDeleteSchema(**result)
