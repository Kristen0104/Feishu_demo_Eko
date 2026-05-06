from __future__ import annotations

import json
import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass
from dataclasses import asdict
from collections import defaultdict, deque
from typing import Any
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

from app.core import redis_client as redis_module

_UNSET = object()
logger = logging.getLogger(__name__)
_WEBSOCKET_SEND_TIMEOUT_SECONDS = 1.0


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    source: str
    title: str
    summary: str
    status: str
    user_id: str | None = None
    chat_id: str | None = None
    message_id: str | None = None
    context_size: int = 0
    instruction: str | None = None
    intent: str | None = None
    artifact: dict[str, Any] | None = None
    context_messages: list[dict[str, Any]] | None = None
    messages: list[dict[str, Any]] | None = None
    opened_at: str = ""
    updated_at: str = ""


class SyncConnectionManager:
    _session_index_key = "eko:sync:sessions:index"
    _event_channel = "eko:sync:events"
    _event_replay_ttl_seconds = 15 * 60

    def __init__(self, *, max_history: int = 32) -> None:
        self._max_history = max_history
        self._origin_id = uuid.uuid4().hex
        self._lock = asyncio.Lock()
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._history: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=self._max_history)
        )
        self._sessions: dict[str, SessionRecord] = {}
        self._redis_listener_task: asyncio.Task[None] | None = None

    def _session_key(self, session_id: str) -> str:
        return f"eko:sync:session:{session_id}"

    def _session_events_key(self, session_id: str) -> str:
        return f"eko:sync:events:{session_id}"

    async def _persist_session(self, record: SessionRecord) -> None:
        redis_client = redis_module.redis_client
        if redis_client is None:
            return

        payload = json.dumps(asdict(record), ensure_ascii=False)
        await redis_client.set(self._session_key(record.session_id), payload)
        await redis_client.zadd(self._session_index_key, {record.session_id: datetime.fromisoformat(record.updated_at).timestamp()})

    def _schedule_redis_write(self, coro: Any, *, label: str) -> None:
        async def runner() -> None:
            try:
                await coro
            except Exception as exc:  # noqa: BLE001
                logger.warning("Sync Redis %s skipped: %s", label, exc)

        asyncio.create_task(runner())

    async def _load_session_from_redis(self, session_id: str) -> SessionRecord | None:
        redis_client = redis_module.redis_client
        if redis_client is None:
            return None

        raw = await redis_client.get(self._session_key(session_id))
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        return SessionRecord(
            session_id=str(data.get("session_id", session_id)),
            source=str(data.get("source", "")),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            status=str(data.get("status", "")),
            user_id=data.get("user_id") if isinstance(data.get("user_id"), str) else None,
            chat_id=data.get("chat_id") if isinstance(data.get("chat_id"), str) else None,
            message_id=data.get("message_id") if isinstance(data.get("message_id"), str) else None,
            context_size=int(data.get("context_size") or 0),
            instruction=data.get("instruction") if isinstance(data.get("instruction"), str) else None,
            intent=data.get("intent") if isinstance(data.get("intent"), str) else None,
            artifact=data.get("artifact") if isinstance(data.get("artifact"), dict) else None,
            context_messages=data.get("context_messages") if isinstance(data.get("context_messages"), list) else [],
            messages=data.get("messages") if isinstance(data.get("messages"), list) else [],
            opened_at=str(data.get("opened_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )

    async def _delete_session_from_redis(self, session_id: str) -> bool:
        redis_client = redis_module.redis_client
        if redis_client is None:
            return False
        deleted = await redis_client.delete(self._session_key(session_id))
        await redis_client.zrem(self._session_index_key, session_id)
        return bool(deleted)

    async def delete_session(self, session_id: str) -> bool:
        removed = False
        async with self._lock:
            if session_id in self._sessions:
                self._sessions.pop(session_id, None)
                removed = True
            peers = self._connections.pop(session_id, None)
            if peers:
                removed = True
            self._history.pop(session_id, None)
        redis_removed = await self._delete_session_from_redis(session_id)
        redis_client = redis_module.redis_client
        if redis_client is not None:
            await redis_client.delete(self._session_events_key(session_id))
        return removed or redis_removed

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[session_id].add(websocket)
            history = list(self._history[session_id])
        replay_history = await self._load_event_history_from_redis(session_id)

        try:
            await websocket.send_json(
                {
                    "type": "SESSION_CONNECTED",
                    "session_id": session_id,
                    "payload": {"transport": "websocket"},
                }
            )

            merged_history = replay_history or history
            for envelope in merged_history:
                await websocket.send_json(envelope)

            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await self.disconnect(session_id, websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            peers = self._connections.get(session_id)
            if not peers:
                return
            peers.discard(websocket)
            if not peers:
                self._connections.pop(session_id, None)

    async def start_redis_forwarder(self) -> None:
        if self._redis_listener_task is not None and not self._redis_listener_task.done():
            return
        if redis_module.redis_client is None:
            return
        self._redis_listener_task = asyncio.create_task(self._run_redis_forwarder())

    async def stop_redis_forwarder(self) -> None:
        task = self._redis_listener_task
        self._redis_listener_task = None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _run_redis_forwarder(self) -> None:
        redis_client = redis_module.redis_client
        if redis_client is None:
            return

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(self._event_channel)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                raw = message.get("data")
                if not isinstance(raw, str):
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict) or payload.get("origin") == self._origin_id:
                    continue
                session_id = payload.get("session_id")
                envelope = payload.get("envelope")
                if isinstance(session_id, str) and isinstance(envelope, dict):
                    await self.emit(session_id, envelope, publish=False)
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(self._event_channel)
            with contextlib.suppress(Exception):
                await pubsub.close()

    async def _publish_event_to_redis(self, session_id: str, envelope: dict[str, Any]) -> None:
        redis_client = redis_module.redis_client
        if redis_client is None:
            return
        serialized_envelope = json.dumps(envelope, ensure_ascii=False)
        events_key = self._session_events_key(session_id)
        pipe = redis_client.pipeline()
        pipe.rpush(events_key, serialized_envelope)
        pipe.ltrim(events_key, -self._max_history, -1)
        pipe.expire(events_key, self._event_replay_ttl_seconds)
        await pipe.execute()
        payload = {
            "origin": self._origin_id,
            "session_id": session_id,
            "envelope": envelope,
        }
        await redis_client.publish(self._event_channel, json.dumps(payload, ensure_ascii=False))

    async def _load_event_history_from_redis(self, session_id: str) -> list[dict[str, Any]]:
        redis_client = redis_module.redis_client
        if redis_client is None:
            return []
        raw_items = await redis_client.lrange(self._session_events_key(session_id), 0, -1)
        history: list[dict[str, Any]] = []
        for raw in raw_items:
            if not isinstance(raw, str):
                continue
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(envelope, dict):
                history.append(envelope)
        return history

    async def emit(self, session_id: str, envelope: dict[str, Any], *, publish: bool = True) -> None:
        async with self._lock:
            self._history[session_id].append(envelope)
            peers = list(self._connections.get(session_id, set()))

        if publish:
            self._schedule_redis_write(
                self._publish_event_to_redis(session_id, envelope),
                label="event publish",
            )

        stale: list[WebSocket] = []
        for websocket in peers:
            try:
                await asyncio.wait_for(
                    websocket.send_json(envelope),
                    timeout=_WEBSOCKET_SEND_TIMEOUT_SECONDS,
                )
            except Exception:
                stale.append(websocket)

        if stale:
            async with self._lock:
                peers = self._connections.get(session_id)
                if peers is None:
                    return
                for websocket in stale:
                    peers.discard(websocket)
                if not peers:
                    self._connections.pop(session_id, None)

    async def register_session(
        self,
        session_id: str,
        *,
        source: str,
        title: str,
        summary: str,
        status: str = "进行中",
        user_id: str | None = None,
        chat_id: str | None = None,
        message_id: str | None = None,
        context_size: int = 0,
        instruction: str | None = None,
        context_messages: list[dict[str, Any]] | None = None,
        intent: str | None = None,
        artifact: dict[str, Any] | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> SessionRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = SessionRecord(
            session_id=session_id,
            source=source,
            title=title,
            summary=summary,
            status=status,
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            context_size=context_size,
            instruction=instruction,
            intent=intent,
            artifact=artifact,
            context_messages=context_messages or [],
            messages=messages or [],
            opened_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._sessions[session_id] = record
        self._schedule_redis_write(self._persist_session(record), label="session persist")
        return record

    async def update_session(
        self,
        session_id: str,
        *,
        status: str | None = None,
        summary: str | None = None,
        context_size: int | None = None,
        intent: str | None | object = _UNSET,
        artifact: dict[str, Any] | None | object = _UNSET,
        context_messages: list[dict[str, Any]] | None | object = _UNSET,
        messages: list[dict[str, Any]] | None | object = _UNSET,
    ) -> SessionRecord | None:
        async with self._lock:
            record = self._sessions.get(session_id)
        if record is None:
            record = await self._load_session_from_redis(session_id)
            if record is None:
                return None
        if status is not None:
            record.status = status
        if summary is not None:
            record.summary = summary
        if context_size is not None:
            record.context_size = context_size
        if intent is not _UNSET:
            record.intent = intent
        if artifact is not _UNSET:
            record.artifact = artifact
        if context_messages is not _UNSET:
            record.context_messages = context_messages
        if messages is not _UNSET:
            record.messages = messages
        record.updated_at = datetime.now(timezone.utc).isoformat()
        async with self._lock:
            self._sessions[session_id] = record
        self._schedule_redis_write(self._persist_session(record), label="session update")
        return record

    async def list_sessions(self, user_id: str | None = None) -> list[SessionRecord]:
        async with self._lock:
            memory_records = {
                record.session_id: record
                for record in self._sessions.values()
                if user_id is None or record.user_id == user_id
            }
        redis_client = redis_module.redis_client
        if redis_client is not None:
            try:
                session_ids = await asyncio.wait_for(redis_client.zrevrange(self._session_index_key, 0, -1), timeout=1.0)
                for session_id in session_ids:
                    record = await asyncio.wait_for(self._load_session_from_redis(session_id), timeout=1.0)
                    if record is None:
                        continue
                    if user_id is not None and record.user_id != user_id:
                        continue
                    existing = memory_records.get(record.session_id)
                    if existing is None or record.updated_at >= existing.updated_at:
                        memory_records[record.session_id] = record
                async with self._lock:
                    for record in memory_records.values():
                        self._sessions[record.session_id] = record
            except Exception as exc:  # noqa: BLE001
                logger.warning("Sync Redis session list skipped: %s", exc)
        return sorted(memory_records.values(), key=lambda record: record.updated_at, reverse=True)

    async def get_session(self, session_id: str, user_id: str | None = None) -> SessionRecord | None:
        async with self._lock:
            memory_record = self._sessions.get(session_id)
        redis_record: SessionRecord | None = None
        if memory_record is not None:
            if user_id is not None and memory_record.user_id != user_id:
                return None
            try:
                redis_record = await asyncio.wait_for(self._load_session_from_redis(session_id), timeout=1.0)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Sync Redis session refresh skipped: %s", exc)
                return memory_record
            if redis_record is None or redis_record.updated_at <= memory_record.updated_at:
                return memory_record
            if user_id is not None and redis_record.user_id != user_id:
                return None
            async with self._lock:
                self._sessions[session_id] = redis_record
            return redis_record
        try:
            record = await asyncio.wait_for(self._load_session_from_redis(session_id), timeout=1.0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sync Redis session load skipped: %s", exc)
            return None
        if record is not None:
            if user_id is not None and record.user_id != user_id:
                return None
            async with self._lock:
                self._sessions[session_id] = record
            return record
        return None


_sync_connection_manager: SyncConnectionManager | None = None


def get_sync_connection_manager() -> SyncConnectionManager:
    global _sync_connection_manager
    if _sync_connection_manager is None:
        _sync_connection_manager = SyncConnectionManager()
    return _sync_connection_manager
