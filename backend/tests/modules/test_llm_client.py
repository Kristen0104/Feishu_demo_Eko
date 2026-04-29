from __future__ import annotations

from app.config import Settings
from app.core.llm_client import LLMClient


def test_llm_client_appends_chat_completions_for_base_endpoint() -> None:
    client = LLMClient(
        settings_override=Settings(
            VOLCENGINE_ENDPOINT="https://ark.cn-beijing.volces.com/api/v3",
        )
    )

    assert client._endpoint == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


def test_llm_client_keeps_explicit_chat_completions_endpoint() -> None:
    client = LLMClient(
        settings_override=Settings(
            VOLCENGINE_ENDPOINT="https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        )
    )

    assert client._endpoint == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
