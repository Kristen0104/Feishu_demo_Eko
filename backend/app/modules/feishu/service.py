from __future__ import annotations

from app.modules.feishu.client import FeishuClient
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


class FeishuService:
    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    def get_card(self, card_id: str) -> FeishuCardSchema:
        return self._client.get_card(card_id)

    def import_diagram(self, payload: FeishuBoardImportRequest) -> FeishuBoardImportSchema:
        return self._client.import_diagram(payload)

    def create_notes(self, payload: FeishuBoardCreateNotesRequest) -> FeishuBoardCreateNotesSchema:
        return self._client.create_notes(payload)

    def get_board_nodes(self, whiteboard_id: str, user_access_token: str | None = None) -> FeishuBoardNodesSchema:
        return self._client.get_board_nodes(whiteboard_id, user_access_token=user_access_token)

    def get_board_image(self, whiteboard_id: str, user_access_token: str | None = None) -> FeishuBoardImageSchema:
        return self._client.get_board_image(whiteboard_id, user_access_token=user_access_token)

    def update_board(self, payload: FeishuBoardUpdateRequest) -> FeishuBoardUpdateSchema:
        return self._client.update_board(payload)

    def delete_board(self, payload: FeishuBoardDeleteRequest) -> FeishuBoardDeleteSchema:
        return self._client.delete_board(payload)
