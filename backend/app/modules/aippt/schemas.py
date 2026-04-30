from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PPTJobStatus = Literal[
    "queued",
    "parsing_file",
    "generating_design",
    "generating_slides",
    "generating_notes",
    "exporting",
    "done",
    "failed",
]
PPTSourceType = Literal["topic", "file", "url"]
PPTDesignMode = Literal["template", "free_design"]


class PPTGenerationRequest(BaseModel):
    topic: str | None = Field(default=None, max_length=4000)
    page_count: int = Field(default=6, ge=1, le=20)
    style: str = Field(default="clean_business", min_length=1, max_length=100)
    design_mode: PPTDesignMode = Field(default="template")
    source_url: str | None = Field(default=None, max_length=2000)


class PPTJobSchema(BaseModel):
    job_id: str
    status: PPTJobStatus
    progress: int
    current_step: str
    source_type: PPTSourceType
    source_name: str | None = None
    page_count: int
    style: str
    design_mode: PPTDesignMode = "template"
    download_url: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class PPTJobRecord(PPTJobSchema):
    source_path: str | None = None
    project_dir: str | None = None
    pptx_path: str | None = None

    def to_public(self) -> PPTJobSchema:
        return PPTJobSchema(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            current_step=self.current_step,
            source_type=self.source_type,
            source_name=self.source_name,
            page_count=self.page_count,
            style=self.style,
            design_mode=self.design_mode,
            download_url=self.download_url,
            error=self.error,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
