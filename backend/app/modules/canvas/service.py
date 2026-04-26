from __future__ import annotations

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import CanvasSessionSchema


class CanvasService:
    def __init__(self, repository: CanvasRepository) -> None:
        # Keep business rules above the repository boundary once canvas state
        # moves beyond this registration-layer stub.
        self._repository = repository

    def get_session(self, session_id: str) -> CanvasSessionSchema:
        return self._repository.get_session(session_id)
