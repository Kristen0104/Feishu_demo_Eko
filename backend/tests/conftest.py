from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_external_api_settings(monkeypatch):
    monkeypatch.setenv("AGENT_API_KEY", "")
    monkeypatch.setenv("VOLCENGINE_API_KEY", "")
    monkeypatch.setenv("FEISHU_APP_ID", "")
    monkeypatch.setenv("FEISHU_APP_SECRET", "")

    from app.config import get_settings
    from app.modules.canvas import dependencies as canvas_dependencies
    from app.modules.feishu import dependencies as feishu_dependencies

    get_settings.cache_clear()
    canvas_dependencies.reset_canvas_dependencies()
    feishu_dependencies.reset_feishu_dependencies()
    yield
    get_settings.cache_clear()
    canvas_dependencies.reset_canvas_dependencies()
    feishu_dependencies.reset_feishu_dependencies()
