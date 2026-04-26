from __future__ import annotations

from app.modules.rag.repository import RagRepository
from app.modules.rag.schemas import RagFileSchema


class RagService:
    def __init__(self, repository: RagRepository) -> None:
        self._repository = repository

    def list_files(self) -> list[RagFileSchema]:
        return self._repository.list_files()
