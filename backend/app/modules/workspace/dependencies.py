from __future__ import annotations

from app.modules.workspace.service import WorkspaceService


def get_workspace_service() -> WorkspaceService:
    return WorkspaceService()
