from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_external_api_settings(monkeypatch):
    monkeypatch.setenv("PPT_USE_LIVE_LLM", "false")
    monkeypatch.setenv("PPT_LLM_TIMEOUT_SECONDS", "180")
    monkeypatch.setenv("PPT_LLM_MAX_TOKENS", "16000")
    monkeypatch.setenv("AGENT_API_KEY", "")
    monkeypatch.setenv("VOLCENGINE_API_KEY", "")
    monkeypatch.setenv("FEISHU_APP_ID", "")
    monkeypatch.setenv("FEISHU_APP_SECRET", "")

    from app.config import get_settings
    from app.modules.ppt import dependencies as ppt_dependencies

    get_settings.cache_clear()
    ppt_dependencies._ppt_service = None
    yield
    get_settings.cache_clear()
    ppt_dependencies._ppt_service = None
