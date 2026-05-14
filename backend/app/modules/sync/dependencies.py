from __future__ import annotations

from app.modules.sync.service import SyncService

_sync_service: SyncService | None = None


def get_sync_service() -> SyncService:
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service
