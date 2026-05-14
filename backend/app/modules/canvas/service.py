from __future__ import annotations

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.schemas import (
    CanvasBoardTaskCreateRequest,
    CanvasBoardTaskLogSchema,
    CanvasBoardTaskSchema,
    CanvasSessionSchema,
)
from app.services.board_generate_service import BoardGenerateService, choose_render_mode


class CanvasService:
    def __init__(
        self,
        repository: CanvasRepository,
        board_generate_service: BoardGenerateService | None = None,
    ) -> None:
        # Keep business rules above the repository boundary once canvas state
        # moves beyond this registration-layer stub.
        self._repository = repository
        self._board_generate_service = board_generate_service

    def get_session(self, session_id: str) -> CanvasSessionSchema:
        return self._repository.get_session(session_id)

    def create_board_task(
        self,
        payload: CanvasBoardTaskCreateRequest,
    ) -> CanvasBoardTaskSchema:
        render_mode = choose_render_mode(payload.message)
        return self._repository.create_board_task(
            payload,
            render_mode=render_mode,
        )

    def get_board_task(self, task_id: str) -> CanvasBoardTaskSchema:
        return self._repository.get_board_task(task_id)

    def run_board_task(self, task_id: str) -> CanvasBoardTaskSchema:
        if self._board_generate_service is None:
            raise RuntimeError("board_generate_service is not configured")

        task = self._repository.get_board_task(task_id)
        running = task.model_copy(
            update={
                "status": "running",
                "current_step": "rendering",
                "logs": [
                    *task.logs,
                    CanvasBoardTaskLogSchema(
                        step="rendering",
                        message="开始执行飞书画板任务",
                    ),
                ],
            }
        )
        self._repository.save_board_task(running)

        try:
            result = self._board_generate_service.generate(
                message=task.message,
                sharing_url=task.sharing_url,
                whiteboard_id=task.whiteboard_id,
            )
        except Exception as exc:  # noqa: BLE001
            failed = running.model_copy(
                update={
                    "status": "failed",
                    "current_step": "failed",
                    "error_message": str(exc),
                    "logs": [
                        *running.logs,
                        CanvasBoardTaskLogSchema(
                            step="failed",
                            message=f"飞书画板任务执行失败: {exc}",
                        ),
                    ],
                }
            )
            return self._repository.save_board_task(failed)

        completed_logs = [
            *running.logs,
            *[
                CanvasBoardTaskLogSchema(step=step, message=message)
                for step, message in result.execution_logs
            ],
            CanvasBoardTaskLogSchema(
                step="succeeded",
                message="飞书画板任务执行完成",
            ),
        ]
        completed = running.model_copy(
            update={
                "status": "succeeded",
                "current_step": "succeeded",
                "whiteboard_id": result.whiteboard_id,
                "render_mode": result.render_mode,
                "preview_url": result.preview_url,
                "ticket_id": result.ticket_id,
                "node_ids": result.node_ids,
                "deleted_count": result.deleted_count,
                "result_summary": result.result_summary,
                "logs": completed_logs,
            }
        )
        return self._repository.save_board_task(completed)
