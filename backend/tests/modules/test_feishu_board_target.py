from __future__ import annotations

from app.modules.feishu.board_target import resolve_board_target_from_sharing_url


def test_resolve_board_target_accepts_board_url() -> None:
    target = resolve_board_target_from_sharing_url(
        "https://example.feishu.cn/wiki/board/wbcnAABBCC"
    )

    assert target.source_kind == "whiteboard"
    assert target.whiteboard_id == "wbcnAABBCC"
    assert target.doc_token is None


def test_resolve_board_target_falls_back_to_document_url() -> None:
    target = resolve_board_target_from_sharing_url(
        "https://example.feishu.cn/docx/AbCdEfGhIjKl"
    )

    assert target.source_kind == "document"
    assert target.doc_token == "AbCdEfGhIjKl"
    assert target.whiteboard_id is None
