from __future__ import annotations

from app.modules.canvas.schemas import CanvasSessionSchema


class CanvasRepository:
    def get_session(self, session_id: str) -> CanvasSessionSchema:
        return CanvasSessionSchema(
            session_id=session_id,
            title="Stub Canvas Session",
        )
