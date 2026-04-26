from __future__ import annotations

from app.modules.rag.schemas import RagFileSchema


class RagRepository:
    def list_files(self) -> list[RagFileSchema]:
        return [
            RagFileSchema(
                file_id="stub-file",
                filename="knowledge-base.md",
                source="stub",
            )
        ]
