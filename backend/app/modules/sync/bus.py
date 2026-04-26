"""Redis/WebSocket broadcast helpers."""

from __future__ import annotations

# TODO(PRD-4.4): move Pub/Sub broadcasts, task progress events, and cursor sync into this module.


async def publish_event(*args, **kwargs):
    raise NotImplementedError("Realtime sync is not implemented yet")

