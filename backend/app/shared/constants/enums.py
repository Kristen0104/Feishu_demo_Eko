from enum import Enum


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    VIEWER = "viewer"


class AgentIntent(str, Enum):
    CHAT = "chat"
    DOC = "doc"
    CANVAS = "canvas"
