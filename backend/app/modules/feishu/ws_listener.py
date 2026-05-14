from __future__ import annotations

import asyncio
from collections import deque
import logging
import signal
import threading
import time
from typing import Any

import lark_oapi as lark

from app.config import settings
from app.core.llm_client import get_llm_client
from app.core.redis_client import close_redis, init_redis
from app.modules.aippt.dependencies import get_aippt_service
from app.modules.canvas.dependencies import get_canvas_service
from app.modules.document.dependencies import get_document_service
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.events import FeishuEventProcessor
from app.modules.sync.dependencies import get_sync_service

logger = logging.getLogger(__name__)
_MAX_TRACKED_MESSAGE_IDS = 1000
_processed_message_ids: set[str] = set()
_processed_message_order: deque[str] = deque()


class AsyncEventRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="feishu-event-runner", daemon=True)
        self._poller_task: asyncio.Future[Any] | None = None

    def start(self) -> None:
        self._thread.start()
        asyncio.run_coroutine_threadsafe(init_redis(), self._loop).result(timeout=15)
        self._start_polling_fallback()

    def submit(self, payload: dict[str, Any]) -> None:
        future = asyncio.run_coroutine_threadsafe(handle_ws_payload(payload), self._loop)
        future.add_done_callback(self._log_result)

    def stop(self) -> None:
        async def shutdown() -> None:
            await close_redis()

        if self._poller_task is not None:
            self._poller_task.cancel()
        try:
            asyncio.run_coroutine_threadsafe(shutdown(), self._loop).result(timeout=15)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)

    def _start_polling_fallback(self) -> None:
        chat_ids = _poll_chat_ids()
        if not chat_ids:
            return
        interval = max(float(settings.FEISHU_WS_POLL_INTERVAL_SECONDS or 5.0), 2.0)
        self._poller_task = asyncio.run_coroutine_threadsafe(
            poll_feishu_mentions(chat_ids=chat_ids, interval_seconds=interval),
            self._loop,
        )
        logger.info("Feishu polling fallback enabled chat_ids=%s interval=%.1fs", ",".join(chat_ids), interval)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    @staticmethod
    def _log_result(future: asyncio.Future[Any]) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("Feishu long-connection event handling failed")


def build_agent_service():
    from app.modules.agent.service import AgentService

    llm_client = get_llm_client()
    feishu_service = get_feishu_service()
    return AgentService(
        llm_client=llm_client,
        feishu_service=feishu_service,
        document_service=get_document_service(llm_client=llm_client, feishu_service=feishu_service),
        aippt_service=get_aippt_service(),
        canvas_service=get_canvas_service(),
        sync_service=get_sync_service(),
    )


async def handle_ws_payload(payload: dict[str, Any]) -> None:
    await handle_feishu_payload(payload, source="long_connection")


async def handle_feishu_payload(payload: dict[str, Any], *, source: str) -> None:
    message_id = _payload_message_id(payload)
    if message_id and not _claim_message_id(message_id):
        logger.info("Skip duplicate Feishu event source=%s message_id=%s", source, message_id)
        return
    processor = FeishuEventProcessor(
        get_feishu_service(),
        build_agent_service(),
        get_sync_service(),
    )
    try:
        await processor.handle(payload)
    except Exception:
        if message_id:
            _release_message_id(message_id)
        raise


def _payload_message_id(payload: dict[str, Any]) -> str | None:
    event = payload.get("event")
    if not isinstance(event, dict):
        return None
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    return _coerce_str(message.get("message_id"))


def _claim_message_id(message_id: str) -> bool:
    if message_id in _processed_message_ids:
        return False
    _processed_message_ids.add(message_id)
    _processed_message_order.append(message_id)
    while len(_processed_message_order) > _MAX_TRACKED_MESSAGE_IDS:
        expired = _processed_message_order.popleft()
        _processed_message_ids.discard(expired)
    return True


def _release_message_id(message_id: str) -> None:
    _processed_message_ids.discard(message_id)


def _poll_chat_ids() -> list[str]:
    raw = settings.FEISHU_WS_POLL_CHAT_IDS
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


async def poll_feishu_mentions(*, chat_ids: list[str], interval_seconds: float) -> None:
    seen: set[str] = set()
    baseline_ms = int(time.time() * 1000)
    last_seen_at_ms: dict[str, int] = {chat_id: baseline_ms for chat_id in chat_ids}
    logger.info("Feishu polling fallback baseline set chat_ids=%s baseline_at_ms=%s", ",".join(chat_ids), baseline_ms)
    while True:
        try:
            await _poll_feishu_mentions_once(chat_ids, seen, last_seen_at_ms)
        except Exception:  # noqa: BLE001
            logger.exception("Feishu polling fallback tick failed")
        await asyncio.sleep(interval_seconds)


async def _poll_feishu_mentions_once(chat_ids: list[str], seen: set[str], last_seen_at_ms: dict[str, int]) -> None:
    feishu_service = get_feishu_service()
    bot_open_id = feishu_service.get_bot_open_id() if hasattr(feishu_service, "get_bot_open_id") else None

    for chat_id in chat_ids:
        before_time_ms = int(time.time() * 1000) + 1000
        watermark = last_seen_at_ms.get(chat_id, 0)
        items = await asyncio.to_thread(
            feishu_service._client.list_recent_chat_messages,  # noqa: SLF001
            chat_id,
            before_time_ms=before_time_ms,
            lookback_minutes=60,
            page_size=20,
            max_pages=2,
        )
        items.sort(key=lambda item: _coerce_int(item.get("create_time")) or 0)
        latest_timestamp = watermark
        mention_count = 0
        handled_count = 0
        for item in items:
            message_id = _coerce_str(item.get("message_id"))
            if not message_id:
                continue
            timestamp = _coerce_int(item.get("create_time")) or 0
            if timestamp:
                latest_timestamp = max(latest_timestamp, timestamp)
            if message_id in seen:
                continue
            if timestamp and timestamp < watermark:
                seen.add(message_id)
                continue
            if _sender_is_app(item):
                seen.add(message_id)
                continue
            if not FeishuEventProcessor.message_mentions_app(item, settings.FEISHU_APP_ID, bot_open_id=bot_open_id):
                seen.add(message_id)
                continue

            mention_count += 1
            payload = _message_item_to_payload(item, chat_id=chat_id)
            logger.info("Feishu polling fallback received message_id=%s chat_id=%s", message_id, chat_id)
            await handle_feishu_payload(payload, source="polling_fallback")
            seen.add(message_id)
            handled_count += 1
        last_seen_at_ms[chat_id] = latest_timestamp
        if items:
            logger.info(
                "Feishu polling fallback scanned chat_id=%s items=%s mentions=%s handled=%s watermark_ms=%s",
                chat_id,
                len(items),
                mention_count,
                handled_count,
                last_seen_at_ms[chat_id],
            )


def _message_item_to_payload(item: dict[str, Any], *, chat_id: str | None = None) -> dict[str, Any]:
    body = item.get("body")
    content = body.get("content") if isinstance(body, dict) else item.get("content")
    if not isinstance(content, str):
        content = ""
    return {
        "schema": "2.0",
        "header": {
            "event_type": "im.message.receive_v1",
        },
        "event": {
            "sender": _poll_sender_to_event_sender(item.get("sender")),
            "message": {
                "chat_id": item.get("chat_id") or chat_id,
                "chat_type": item.get("chat_type") or "group",
                "content": content,
                "create_time": item.get("create_time"),
                "mentions": item.get("mentions") if isinstance(item.get("mentions"), list) else [],
                "message_id": item.get("message_id"),
                "message_type": item.get("message_type") or item.get("msg_type") or "text",
                "update_time": item.get("update_time"),
            },
        },
    }


def _poll_sender_to_event_sender(sender: Any) -> dict[str, Any]:
    if not isinstance(sender, dict):
        return {}
    sender_id: dict[str, Any] = {}
    sender_open_id = sender.get("open_id") or sender.get("id")
    if isinstance(sender_open_id, str):
        sender_id["open_id"] = sender_open_id
    union_id = sender.get("union_id")
    if isinstance(union_id, str):
        sender_id["union_id"] = union_id
    user_id = sender.get("user_id")
    if isinstance(user_id, str):
        sender_id["user_id"] = user_id
    return {
        "sender_id": sender_id,
        "sender_type": sender.get("sender_type"),
        "tenant_key": sender.get("tenant_key"),
    }


def _sender_is_app(item: dict[str, Any]) -> bool:
    sender = item.get("sender")
    if not isinstance(sender, dict):
        return False
    return sender.get("sender_type") in {"app", "bot", "application"} or sender.get("id_type") == "app_id"


def _coerce_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def event_to_http_payload(event: Any) -> dict[str, Any]:
    event_data = getattr(event, "event", None)
    message = getattr(event_data, "message", None)
    sender = getattr(event_data, "sender", None)

    return {
        "schema": "2.0",
        "header": {
            "event_type": "im.message.receive_v1",
        },
        "event": {
            "sender": _object_to_plain(sender),
            "message": _object_to_plain(message),
        },
    }


def _object_to_plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_object_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _object_to_plain(item) for key, item in value.items()}

    result: dict[str, Any] = {}
    for key, item in vars(value).items():
        if key.startswith("_") or item is None:
            continue
        result[key] = _object_to_plain(item)
    return result


def build_event_handler(runner: AsyncEventRunner):
    def on_message_receive(event: Any) -> None:
        payload = event_to_http_payload(event)
        message = payload.get("event", {}).get("message", {})
        logger.info(
            "Feishu WS event received message_id=%s chat_id=%s",
            message.get("message_id"),
            message.get("chat_id"),
        )
        runner.submit(payload)

    return (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_message_receive)
        .build()
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.FEISHU_APP_ID or not settings.FEISHU_APP_SECRET:
        raise RuntimeError("FEISHU_APP_ID and FEISHU_APP_SECRET are required for Feishu long connection")

    runner = AsyncEventRunner()
    runner.start()

    client = lark.ws.Client(
        settings.FEISHU_APP_ID,
        settings.FEISHU_APP_SECRET,
        event_handler=build_event_handler(runner),
        log_level=lark.LogLevel.DEBUG if settings.DEBUG else lark.LogLevel.INFO,
    )

    def stop(signum: int, _frame: Any) -> None:
        logger.info("Stopping Feishu long connection on signal %s", signum)
        runner.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    logger.info("Starting Feishu long connection listener")
    client.start()


if __name__ == "__main__":
    main()
