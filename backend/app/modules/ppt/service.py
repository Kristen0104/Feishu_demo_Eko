from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.modules.ppt.repository import PptRepository
from app.modules.ppt.schemas import (
    PptTaskCreateRequest,
    PptTaskLogSchema,
    PptTaskSchema,
)
from app.services.ppt_html_generate_service import PptHtmlGenerateService
from app.services.pptx_export_service import PptxExportService


class PptService:
    def __init__(
        self,
        repository: PptRepository,
        generate_service: PptHtmlGenerateService | object | None = None,
        export_service: PptxExportService | object | None = None,
        generated_root: Path | None = None,
    ) -> None:
        self._repository = repository
        self._generate_service = generate_service or PptHtmlGenerateService()
        self._export_service = export_service or PptxExportService()
        self._generated_root = generated_root or Path(get_settings().GENERATED_ROOT)

    def create_task(self, payload: PptTaskCreateRequest) -> PptTaskSchema:
        return self._repository.create_task(payload)

    def get_task(self, task_id: str) -> PptTaskSchema:
        return self._repository.get_task(task_id)

    def run_task(self, task_id: str) -> PptTaskSchema:
        task = self._repository.get_task(task_id)
        running = task.model_copy(
            update={
                "status": "running",
                "current_step": "generating",
                "logs": [
                    *task.logs,
                    PptTaskLogSchema(
                        step="generating",
                        message="PPT HTML generation started.",
                    ),
                ],
            }
        )
        self._repository.save_task(running)

        try:
            html = self._generate_service.generate_html(
                topic=task.topic,
                prompt=task.prompt,
                title=task.title,
            )
            artifact_dir = self._generated_root / "ppt_html" / task.task_id
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = artifact_dir / "index.html"
            artifact_path.write_text(html, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            failed = running.model_copy(
                update={
                    "status": "failed",
                    "current_step": "failed",
                    "error_message": str(exc),
                    "logs": [
                        *running.logs,
                        PptTaskLogSchema(
                            step="failed",
                            message=f"PPT HTML generation failed: {exc}",
                        ),
                    ],
                }
            )
            return self._repository.save_task(failed)

        succeeded = running.model_copy(
            update={
                "status": "succeeded",
                "current_step": "succeeded",
                "artifact_path": str(artifact_path),
                "preview_url": f"/api/v1/ppt/tasks/{task.task_id}/preview",
                "pptx_status": "pending",
                "pptx_current_step": "pending",
                "pptx_path": None,
                "pptx_download_url": None,
                "pptx_error_message": None,
                "logs": [
                    *running.logs,
                    PptTaskLogSchema(
                        step="saving",
                        message=f"Saved generated HTML to {artifact_path}.",
                    ),
                    PptTaskLogSchema(
                        step="succeeded",
                        message="PPT HTML generation completed.",
                    ),
                ],
            }
        )
        return self._repository.save_task(succeeded)

    def export_pptx(self, task_id: str) -> PptTaskSchema:
        task = self._repository.get_task(task_id)
        if task.artifact_path is None:
            raise ValueError("HTML artifact not found for PPTX export")

        exporting = task.model_copy(
            update={
                "pptx_status": "running",
                "pptx_current_step": "exporting",
                "pptx_error_message": None,
                "logs": [
                    *task.logs,
                    PptTaskLogSchema(
                        step="exporting_pptx",
                        message="PPTX export started.",
                    ),
                ],
            }
        )
        self._repository.save_task(exporting)

        try:
            export_dir = self._generated_root / "ppt_html" / task.task_id / "pptx_export"
            result = self._export_service.export(
                html_path=Path(task.artifact_path),
                output_dir=export_dir,
                deck_title=task.title or task.topic,
            )
        except Exception as exc:  # noqa: BLE001
            failed = exporting.model_copy(
                update={
                    "pptx_status": "failed",
                    "pptx_current_step": "failed",
                    "pptx_error_message": str(exc),
                    "logs": [
                        *exporting.logs,
                        PptTaskLogSchema(
                            step="failed",
                            message=f"PPTX export failed: {exc}",
                        ),
                    ],
                }
            )
            return self._repository.save_task(failed)

        succeeded = exporting.model_copy(
            update={
                "pptx_status": "succeeded",
                "pptx_current_step": "succeeded",
                "pptx_path": result["pptx_path"],
                "pptx_download_url": f"/api/v1/ppt/tasks/{task.task_id}/download-pptx",
                "logs": [
                    *exporting.logs,
                    PptTaskLogSchema(
                        step="succeeded",
                        message="PPTX export completed.",
                    ),
                ],
            }
        )
        return self._repository.save_task(succeeded)
