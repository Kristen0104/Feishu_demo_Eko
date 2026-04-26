from __future__ import annotations

from app.modules.sync.service import SyncService


def get_sync_service() -> SyncService:
    return SyncService()
