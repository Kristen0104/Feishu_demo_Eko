from __future__ import annotations

from importlib import import_module
from typing import Final

from fastapi import FastAPI

ROUTER_REGISTRY: Final[tuple[tuple[str, str], ...]] = (
    ("app.modules.system.router", ""),
    ("app.modules.auth.router", "/api/v1/auth"),
    ("app.modules.document.router", "/api/v1/document"),
    ("app.modules.canvas.router", "/api/v1/canvas"),
    ("app.modules.canvas.ui_router", ""),
    ("app.modules.agent.router", "/api/v1/agent"),
    ("app.modules.rag.router", "/api/v1/rag"),
    ("app.modules.feishu.router", "/api/v1/feishu"),
    ("app.modules.ppt.router", "/api/v1/ppt"),
    ("app.modules.aippt.router", "/api/v1/ppt"),
    ("app.modules.workspace.router", "/api/v1/workspace"),
    ("app.modules.sync.router", "/api/v1/sync"),
)


def _load_router(module_path: str):
    return import_module(module_path).router


def register_routers(app: FastAPI) -> None:
    for module_path, prefix in ROUTER_REGISTRY:
        router = _load_router(module_path)
        if prefix:
            app.include_router(router, prefix=prefix)
        else:
            app.include_router(router)
