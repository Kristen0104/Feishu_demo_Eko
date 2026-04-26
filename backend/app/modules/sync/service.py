from __future__ import annotations

from app.modules.sync.schemas import SyncChannelSchema


class SyncService:
    def get_channel(self, session_id: str) -> SyncChannelSchema:
        return SyncChannelSchema(session_id=session_id)
