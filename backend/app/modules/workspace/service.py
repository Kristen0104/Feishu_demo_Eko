from __future__ import annotations

from app.modules.workspace.schemas import WorkspaceSchema


class WorkspaceService:
    def get_workspace(self, workspace_id: str) -> WorkspaceSchema:
        return WorkspaceSchema(
            workspace_id=workspace_id,
            role="owner",
            locked=False,
        )
