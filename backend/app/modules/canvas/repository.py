from __future__ import annotations

from uuid import uuid4

from app.modules.canvas.schemas import (
    CanvasBoardTaskCreateRequest,
    CanvasBoardTaskSchema,
    CanvasSessionSchema,
)


class CanvasRepository:
    def __init__(self) -> None:
        self._board_tasks: dict[str, CanvasBoardTaskSchema] = {}

    def get_session(self, session_id: str) -> CanvasSessionSchema:
        return CanvasSessionSchema(
            session_id=session_id,
            title="Stub Canvas Session",
        )

    def create_board_task(
        self,
        payload: CanvasBoardTaskCreateRequest,
        *,
        render_mode: str,
    ) -> CanvasBoardTaskSchema:
        task = CanvasBoardTaskSchema(
            task_id=f"board-task-{uuid4().hex[:12]}",
            message=payload.message,
            sharing_url=payload.sharing_url,
            title=payload.title,
            render_mode=render_mode,
        )
        self._board_tasks[task.task_id] = task
        return task

    def get_board_task(self, task_id: str) -> CanvasBoardTaskSchema:
        return self._board_tasks[task_id]

    def save_board_task(self, task: CanvasBoardTaskSchema) -> CanvasBoardTaskSchema:
        self._board_tasks[task.task_id] = task
        return task
