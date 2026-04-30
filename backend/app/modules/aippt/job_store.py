from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from app.modules.aippt.schemas import PPTJobRecord


class JobStore:
    def __init__(self, jobs_root: Path, uploads_root: Path, projects_root: Path, exports_root: Path) -> None:
        self.jobs_root = jobs_root
        self.uploads_root = uploads_root
        self.projects_root = projects_root
        self.exports_root = exports_root
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self.uploads_root.mkdir(parents=True, exist_ok=True)
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.exports_root.mkdir(parents=True, exist_ok=True)

    def write(self, record: PPTJobRecord) -> None:
        self.job_file(record.job_id).write_text(
            json.dumps(record.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def read(self, job_id: str) -> PPTJobRecord:
        path = self.job_file(job_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="PPT job not found.")
        return PPTJobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def job_file(self, job_id: str) -> Path:
        return self.jobs_root / f"{job_id}.json"

    def upload_dir(self, job_id: str) -> Path:
        return self.uploads_root / job_id

    def project_dir(self, job_id: str) -> Path:
        return self.projects_root / job_id

    def export_file(self, job_id: str) -> Path:
        return self.exports_root / f"{job_id}.pptx"
