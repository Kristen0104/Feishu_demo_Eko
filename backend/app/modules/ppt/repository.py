from __future__ import annotations

from uuid import uuid4

from app.modules.ppt.schemas import PptTaskCreateRequest, PptTaskSchema


class PptRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, PptTaskSchema] = {}

    def create_task(self, payload: PptTaskCreateRequest) -> PptTaskSchema:
        task_id = f"ppt-task-{uuid4().hex[:12]}"
        task = PptTaskSchema(
            task_id=task_id,
            topic=payload.topic,
            prompt=payload.prompt,
            title=payload.title,
            preview_url=f"/api/v1/ppt/tasks/{task_id}/preview",
        )
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> PptTaskSchema:
        return self._tasks[task_id]

    def save_task(self, task: PptTaskSchema) -> PptTaskSchema:
        self._tasks[task.task_id] = task
        return task
