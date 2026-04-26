from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AgentTaskSchema(BaseModel):
    task_id: str
    status: Literal["accepted"] = "accepted"
