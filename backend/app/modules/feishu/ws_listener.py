from __future__ import annotations

import asyncio
import logging
import signal
import threading
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


class AsyncEventRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="feishu-event-runner", daemon=True)

    def start(self) -> None:
        self._thread.start()
        asyncio.run_coroutine_threadsafe(init_redis(), self._loop).result(timeout=15)

    def submit(self, payload: dict[str, Any]) -> None:
        future = asyncio.run_coroutine_threadsafe(handle_ws_payload(payload), self._loop)
        future.add_done_callback(self._log_result)

    def stop(self) -> None:
        async def shutdown() -> None:
            await close_redis()
            self._loop.stop()

        asyncio.run_coroutine_threadsafe(shutdown(), self._loop).result(timeout=15)
        self._thread.join(timeout=5)

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
    processor = FeishuEventProcessor(
        get_feishu_service(),
        build_agent_service(),
        get_sync_service(),
    )
    await processor.handle(payload)


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
