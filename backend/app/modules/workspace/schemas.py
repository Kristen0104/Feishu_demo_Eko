from __future__ import annotations

from pydantic import BaseModel


class WorkspaceSchema(BaseModel):
    workspace_id: str
    role: str
    locked: bool
