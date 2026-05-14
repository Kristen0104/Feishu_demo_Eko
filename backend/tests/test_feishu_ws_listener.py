from __future__ import annotations

from app.modules.feishu.ws_listener import _claim_message_id, _message_item_to_payload, _release_message_id


def test_poll_message_item_payload_uses_configured_chat_id_when_openapi_item_omits_it() -> None:
    payload = _message_item_to_payload(
        {
            "message_id": "om_test",
            "message_type": "text",
            "body": {"content": '{"text":"@_user_1 生成文档"}'},
            "mentions": [{"key": "@_user_1", "id": "cli_test", "id_type": "app_id"}],
            "sender": {"open_id": "ou_user", "sender_type": "user"},
        },
        chat_id="oc_test",
    )

    message = payload["event"]["message"]
    assert message["chat_id"] == "oc_test"
    assert message["content"] == '{"text":"@_user_1 生成文档"}'
    assert message["message_id"] == "om_test"
    assert payload["event"]["sender"]["sender_id"]["open_id"] == "ou_user"


def test_claim_message_id_dedupes_until_released() -> None:
    _release_message_id("om_duplicate")

    assert _claim_message_id("om_duplicate") is True
    assert _claim_message_id("om_duplicate") is False

    _release_message_id("om_duplicate")
    assert _claim_message_id("om_duplicate") is True
    _release_message_id("om_duplicate")
