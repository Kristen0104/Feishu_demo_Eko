from __future__ import annotations

import asyncio
from collections import deque
import json
import logging
import re
from typing import TYPE_CHECKING, Any

try:
    from lark_oapi.core.utils import AESCipher
except ImportError:  # pragma: no cover - optional dependency for encrypted events
    AESCipher = None

from app.config import settings
from app.core import redis_client as redis_module
from app.core.database import AsyncSessionLocal
from app.modules.agent.schemas import AgentChatArtifact, AgentChatRequest, AgentIntent
from app.modules.auth.repository import AuthRepository
from app.modules.feishu.service import FeishuService
from app.modules.sync.service import SyncService

if TYPE_CHECKING:
    from app.modules.agent.service import AgentService

logger = logging.getLogger(__name__)
_MENTION_TAG_RE = re.compile(r"<at[^>]*>.*?</at>", re.IGNORECASE | re.DOTALL)
_MAX_DEDUPED_MESSAGE_IDS = 1000
_DEDUPED_MESSAGE_TTL_SECONDS = 24 * 60 * 60
VAGUE_CLARIFICATION_QUESTION = "请问你想整理什么内容？是整理刚才的对话记录，还是其他信息？另外，你希望整理成什么形式？比如摘要、要点列表，或者生成一个文档？"
_deduped_message_ids: set[str] = set()
_deduped_message_order: deque[str] = deque()


async def _claim_deduped_message_id(message_id: str) -> bool:
    redis_client = redis_module.redis_client
    if redis_client is not None:
        try:
            claimed = await redis_client.set(
                f"eko:feishu:event:dedupe:{message_id}",
                "1",
                ex=_DEDUPED_MESSAGE_TTL_SECONDS,
                nx=True,
            )
            return bool(claimed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Feishu Redis event dedupe skipped message_id=%s: %s", message_id, exc)

    if message_id in _deduped_message_ids:
        return False
    _deduped_message_ids.add(message_id)
    _deduped_message_order.append(message_id)
    while len(_deduped_message_order) > _MAX_DEDUPED_MESSAGE_IDS:
        expired = _deduped_message_order.popleft()
        _deduped_message_ids.discard(expired)
    return True


class FeishuEventProcessor:
    def __init__(
        self,
        feishu_service: FeishuService,
        agent_service: AgentService,
        sync_service: SyncService | None = None,
        dedupe_events: bool = False,
    ) -> None:
        self._feishu_service = feishu_service
        self._agent_service = agent_service
        self._sync_service = sync_service
        self._bot_open_id: str | None = None
        self._dedupe_events = dedupe_events

    async def handle(self, payload: dict[str, Any]) -> dict[str, str]:
        envelope = self._unwrap_payload(payload)
        challenge = envelope.get("challenge")
        if isinstance(challenge, str) and challenge:
            return {"challenge": challenge}

        self._validate_verification_token(envelope)

        event_type = self._event_type(envelope)
        if event_type != "im.message.receive_v1":
            return {"msg": "success"}

        event = envelope.get("event")
        if not isinstance(event, dict):
            return {"msg": "success"}

        message = event.get("message")
        if not isinstance(message, dict):
            return {"msg": "success"}

        if not self._should_handle_message(message):
            logger.info(
                "Feishu event ignored because bot was not mentioned chat_id=%s message_id=%s chat_type=%s",
                message.get("chat_id"),
                message.get("message_id"),
                message.get("chat_type"),
            )
            return {"msg": "success"}

        command_text = self._extract_command_text(message)
        if not command_text:
            return {"msg": "success"}

        if command_text.startswith("/"):
            command_name, command_target, command_prompt = self._parse_trigger_command(command_text)
        else:
            command_name, command_target, command_prompt = "new", None, command_text

        if command_name == "invalid":
            logger.info("Feishu event ignored because slash command is unsupported: %s", command_text)
            return {"msg": "success"}

        chat_id = self._coerce_str(message.get("chat_id"))
        message_id = self._coerce_str(message.get("message_id"))
        create_time = self._coerce_int(message.get("create_time"))
        if not chat_id or not message_id:
            logger.info("Feishu event ignored because chat_id/message_id is missing")
            return {"msg": "success"}
        if self._dedupe_events and not await _claim_deduped_message_id(message_id):
            logger.info("Feishu event ignored because message_id was already processed: %s", message_id)
            return {"msg": "success"}

        if command_name == "chat":
            return await self._handle_chat_command(command_target, command_prompt)

        session_id = f"feishu:{chat_id}:{message_id}"
        if command_name == "new":
            instruction = self._normalize_instruction(command_prompt)
            sender_profile = self._build_fast_sender_profile(event.get("sender"))
            resolved_profile = await self._resolve_sender_profile(event.get("sender"))
            trigger_message = self._build_user_message(
                instruction,
                timestamp=create_time,
                sender_profile=sender_profile,
            )
            if self._needs_new_session_clarification(instruction):
                assistant_message = {
                    "role": "assistant",
                    "content": VAGUE_CLARIFICATION_QUESTION,
                }
                if self._sync_service is not None:
                    await self._sync_service.publish_session_opened(
                        session_id,
                        source="feishu",
                        user_id=resolved_profile.get("platform_user_id"),
                        chat_id=chat_id,
                        message_id=message_id,
                        context_size=0,
                        instruction=instruction,
                        context_messages=[],
                        status="等待确认意图",
                        summary=VAGUE_CLARIFICATION_QUESTION,
                        messages=[trigger_message, assistant_message],
                        route_state={
                            "state": "awaiting_clarification",
                            "clarification_type": "organize_request",
                            "original_message": instruction,
                            "slots": {},
                            "required_slots": ["content_scope", "output_format"],
                            "options": {
                                "content_scope": ["recent_chat", "other_information"],
                                "output_format": ["summary", "bullet_list", "minutes", "document"],
                            },
                        },
                    )
                    logger.info("Feishu vague direct mention opened clarification session=%s", session_id)
                await self._send_workspace_link_to_chat(chat_id, session_id)
                await self._feishu_service.send_text_message_to_chat(chat_id, VAGUE_CLARIFICATION_QUESTION)
                return {"msg": "success"}

            if self._sync_service is not None:
                await self._sync_service.publish_session_opened(
                    session_id,
                    source="feishu",
                    user_id=resolved_profile.get("platform_user_id"),
                    chat_id=chat_id,
                    message_id=message_id,
                    context_size=0,
                    instruction=instruction,
                    context_messages=[],
                    status="进行中",
                    summary="收到 @机器人 消息，正在读取群聊上下文并继续处理。",
                    messages=[trigger_message],
                )
                logger.info(
                    "Feishu direct mention opened session=%s before loading context",
                    session_id,
                )
                await self._sync_service.publish_agent_message(
                    session_id,
                    role="assistant",
                    content="收到。我先读取群聊上下文，并继续处理。",
                )
            await self._send_workspace_link_to_chat(chat_id, session_id)
            self._schedule_new_session_bootstrap(
                session_id=session_id,
                chat_id=chat_id,
                before_time_ms=create_time,
                instruction=instruction,
                sender_profile=resolved_profile,
            )
            logger.info("Feishu direct mention bootstrapped session=%s", session_id)
            return {"msg": "success"}

        return {"msg": "success"}

    def _unwrap_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        encrypted = payload.get("encrypt")
        if not isinstance(encrypted, str) or not encrypted:
            return payload

        if AESCipher is None:
            raise RuntimeError("Encrypted Feishu events require the optional lark_oapi dependency")

        if not settings.FEISHU_ENCRYPT_KEY:
            raise ValueError("Feishu encrypt_key is required for encrypted events")

        plaintext = AESCipher(settings.FEISHU_ENCRYPT_KEY).decrypt_str(encrypted)
        data = json.loads(plaintext)
        if not isinstance(data, dict):
            raise ValueError("Encrypted Feishu event did not decode to an object")
        return data

    def _validate_verification_token(self, payload: dict[str, Any]) -> None:
        expected = settings.FEISHU_VERIFICATION_TOKEN
        if not expected:
            return

        token = payload.get("token")
        if not isinstance(token, str) or not token:
            header = payload.get("header")
            if isinstance(header, dict):
                token = header.get("token") if isinstance(header.get("token"), str) else None

        if token != expected:
            raise ValueError("Invalid Feishu verification token")

    def _event_type(self, payload: dict[str, Any]) -> str:
        header = payload.get("header")
        if isinstance(header, dict):
            event_type = header.get("event_type")
            if isinstance(event_type, str):
                return event_type
        event_type = payload.get("type")
        return event_type if isinstance(event_type, str) else ""

    def _should_handle_message(self, message: dict[str, Any]) -> bool:
        if self._is_private_chat(message):
            return True
        return self._mentions_this_bot(message)

    def _is_private_chat(self, message: dict[str, Any]) -> bool:
        chat_type = str(message.get("chat_type") or "").strip().lower()
        return chat_type in {"p2p", "private", "single"}

    def _mentions_this_bot(self, message: dict[str, Any]) -> bool:
        mentions = message.get("mentions")
        app_id = settings.FEISHU_APP_ID.strip() if isinstance(settings.FEISHU_APP_ID, str) else ""
        bot_open_id = self._get_bot_open_id()
        if self.message_mentions_app(message, app_id, bot_open_id=bot_open_id):
            return True

        text = self._extract_raw_message_text(message)
        if self._text_might_mention_bot(text):
            logger.info(
                "Feishu mention fallback matched by text chat_id=%s message_id=%s text=%s",
                message.get("chat_id"),
                message.get("message_id"),
                text[:120],
            )
            return True

        if not isinstance(mentions, list) or not mentions:
            return False

        for mention in mentions:
            if not isinstance(mention, dict):
                continue
            mention_open_id = self._mention_open_id(mention)
            if mention_open_id and mention_open_id == bot_open_id:
                return True
            logger.info(
                "Feishu mention did not match bot app_id=%s mention_id_type=%s mention_id=%s mentioned_type=%s mention_open_id=%s bot_open_id=%s",
                app_id,
                mention.get("id_type"),
                mention.get("id"),
                mention.get("mentioned_type"),
                mention_open_id,
                bot_open_id,
            )
        return False

    @staticmethod
    def message_mentions_app(message: dict[str, Any], app_id: str, bot_open_id: str | None = None) -> bool:
        if not app_id and not bot_open_id:
            return False
        mentions = message.get("mentions")
        if not isinstance(mentions, list):
            return False
        for mention in mentions:
            if not isinstance(mention, dict):
                continue
            if app_id and mention.get("id_type") == "app_id" and mention.get("id") == app_id:
                return True
            if bot_open_id:
                mention_id = mention.get("id")
                if isinstance(mention_id, str) and mention.get("id_type") == "open_id" and mention_id == bot_open_id:
                    return True
                if isinstance(mention_id, dict) and mention_id.get("open_id") == bot_open_id:
                    return True
        return False

    def _extract_raw_message_text(self, message: dict[str, Any]) -> str:
        body = message.get("content")
        text = ""
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                parsed_text = parsed.get("text")
                if isinstance(parsed_text, str):
                    text = parsed_text
            if not text:
                text = body
        return " ".join(text.split()).strip()

    def _text_might_mention_bot(self, text: str) -> bool:
        if not text:
            return False
        normalized = text.casefold()
        configured_bot_name = getattr(settings, "FEISHU_BOT_NAME", "")
        bot_name = configured_bot_name.casefold() if isinstance(configured_bot_name, str) and configured_bot_name else ""
        candidates = [candidate for candidate in (bot_name, "eko_test", "eko test", "eko") if candidate]
        return any(f"@{candidate}" in normalized for candidate in candidates)

    async def _send_workspace_link_to_chat(self, chat_id: str, session_id: str) -> None:
        if not chat_id:
            return
        workspace_url = f"http://127.0.0.1:3002/sessions/{session_id}"
        try:
            await self._feishu_service.send_text_message_to_chat(
                chat_id,
                f"Eko 会话已创建，工作台链接：\n{workspace_url}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Send workspace link while waiting for selection failed session=%s: %s", session_id, exc)

    def _get_bot_open_id(self) -> str | None:
        if self._bot_open_id:
            return self._bot_open_id
        if hasattr(self._feishu_service, "get_bot_open_id"):
            try:
                bot_open_id = self._feishu_service.get_bot_open_id()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Feishu bot open_id lookup failed: %s", exc)
                return None
            if isinstance(bot_open_id, str) and bot_open_id:
                self._bot_open_id = bot_open_id
        return self._bot_open_id

    def _mention_open_id(self, mention: dict[str, Any]) -> str | None:
        mention_id = mention.get("id")
        if isinstance(mention_id, str) and mention.get("id_type") == "open_id":
            return mention_id
        if isinstance(mention_id, dict):
            open_id = mention_id.get("open_id")
            if isinstance(open_id, str) and open_id:
                return open_id
        open_id = mention.get("open_id")
        return open_id if isinstance(open_id, str) and open_id else None

    def _extract_command_text(self, message: dict[str, Any]) -> str:
        text = self._extract_raw_message_text(message)
        text = self._strip_message_mentions(text, message)
        return " ".join(text.split()).strip()

    def _strip_message_mentions(self, text: str, message: dict[str, Any]) -> str:
        stripped = _MENTION_TAG_RE.sub("", text)
        mentions = message.get("mentions")
        if not isinstance(mentions, list):
            return stripped
        for mention in mentions:
            if not isinstance(mention, dict):
                continue
            key = mention.get("key")
            if isinstance(key, str) and key:
                stripped = stripped.replace(key, "")
            name = mention.get("name")
            if isinstance(name, str) and name:
                stripped = stripped.replace(name, "")
        return stripped

    def _normalize_instruction(self, text: str) -> str:
        instruction = " ".join(text.split()).strip()
        lowered = instruction.lower()
        prefixes = ("message:", "message", "消息:", "消息")
        for prefix in prefixes:
            if lowered == prefix:
                return "请基于最近群聊上下文继续回复。"
            if lowered.startswith(f"{prefix} "):
                instruction = instruction[len(prefix) :].strip()
                break
        return instruction or "请基于最近群聊上下文继续回复。"

    def _needs_new_session_clarification(self, instruction: str) -> bool:
        compact = re.sub(r"[\s，。！？!?、,.；;：:（）()【】\[\]「」『』\"'“”‘’]+", "", instruction).lower()
        if not compact:
            return True

        explicit_keywords = (
            "ppt",
            "powerpoint",
            "docx",
            "word",
            "文档",
            "飞书文档",
            "画板",
            "白板",
            "图表",
            "饼图",
            "摘要",
            "要点",
            "列表",
            "会议纪要",
            "周报",
            "报告",
            "聊天记录",
            "对话记录",
            "刚才",
            "上下文",
            "群聊",
            "生成",
            "写",
            "做",
            "创建",
            "输出",
        )
        if any(keyword in compact for keyword in explicit_keywords):
            return False

        vague_requests = {
            "整理",
            "整理下",
            "整理一下",
            "帮我整理",
            "帮我整理下",
            "帮我整理一下",
            "麻烦整理",
            "麻烦整理下",
            "麻烦整理一下",
            "请整理",
            "请整理下",
            "请整理一下",
        }
        return compact in vague_requests

    def _parse_trigger_command(self, text: str) -> tuple[str, str | None, str]:
        stripped = " ".join(text.split()).strip()
        if not stripped:
            return "invalid", None, ""

        command, _, remainder = stripped.partition(" ")
        command = command.lower()
        remainder = remainder.strip()

        if command == "/chat":
            session_id, _, prompt = remainder.partition(" ")
            session_id = session_id.strip()
            if not session_id:
                return "invalid", None, ""
            return "chat", session_id, prompt.strip()

        return "invalid", None, ""

    async def _handle_chat_command(self, session_id: str | None, prompt: str) -> dict[str, str]:
        if not session_id:
            logger.info("Feishu /chat ignored because session_id is missing")
            return {"msg": "success"}

        instruction = self._normalize_instruction(prompt)
        sender_profile: dict[str, Any] = {}
        if self._sync_service is not None:
            session = await self._sync_service.get_session(session_id)
            if session is None:
                await self._sync_service.publish_error(
                    session_id,
                    "会话不存在，无法继续对话。",
                    error="session not found",
                )
                logger.info("Feishu /chat rejected missing session=%s", session_id)
                return {"msg": "success"}
            if session.user_id:
                sender_profile["platform_user_id"] = session.user_id

        request = AgentChatRequest(
            session_id=session_id,
            message=instruction,
            context=AgentContext(chat_history=[]),
            sender=sender_profile or None,
        )
        await self._run_agent_stream_to_session(request)
        logger.info("Feishu /chat forwarded message to session=%s", session_id)
        return {"msg": "success"}

    def _schedule_agent_chat(self, request: AgentChatRequest) -> None:
        task = asyncio.create_task(self._run_agent_stream_to_session(request))
        task.add_done_callback(lambda finished: self._log_agent_task_result(request.session_id, finished))

    def _schedule_new_session_bootstrap(
        self,
        *,
        session_id: str,
        chat_id: str,
        before_time_ms: int | None,
        instruction: str,
        sender_profile: dict[str, Any] | None,
    ) -> None:
        task = asyncio.create_task(
            self._bootstrap_new_session(
                session_id=session_id,
                chat_id=chat_id,
                before_time_ms=before_time_ms,
                instruction=instruction,
                sender_profile=sender_profile,
            )
        )
        task.add_done_callback(lambda finished: self._log_agent_task_result(session_id, finished))

    async def _load_context_candidates(
        self,
        *,
        session_id: str,
        chat_id: str,
        before_time_ms: int | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._feishu_service.get_chat_context_candidates,
                chat_id,
                before_time_ms=before_time_ms,
                limit=limit,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Feishu context fetch failed; continuing with empty context session=%s chat=%s: %s",
                session_id,
                chat_id,
                exc,
            )
            return []

    async def _bootstrap_new_session(
        self,
        *,
        session_id: str,
        chat_id: str,
        before_time_ms: int | None,
        instruction: str,
        sender_profile: dict[str, Any] | None,
    ) -> None:
        context_candidates = await self._load_context_candidates(
            session_id=session_id,
            chat_id=chat_id,
            before_time_ms=before_time_ms,
            limit=15,
        )
        if self._sync_service is not None:
            await self._sync_service.update_session_context(
                session_id,
                context_size=len(context_candidates),
                context_messages=context_candidates,
                selected_context_messages=context_candidates,
                status="进行中",
                summary=f"已读取 {len(context_candidates)} 条候选消息，继续生成中。",
            )
            logger.info(
                "Feishu direct mention loaded session=%s with %s context candidates",
                session_id,
                len(context_candidates),
            )
            request = AgentChatRequest(
                session_id=session_id,
                message=instruction,
                sender=sender_profile,
            )
            self._schedule_agent_chat(request)

    async def _resolve_current_artifact_for_followup(
        self,
        chat_id: str,
        session_id: str,
        instruction: str,
    ) -> AgentChatArtifact | None:
        if self._sync_service is None or not self._looks_like_existing_artifact_update(instruction):
            return None
        if not hasattr(self._sync_service, "list_sessions"):
            return None
        try:
            sessions = await self._sync_service.list_sessions()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Resolve latest Feishu artifact skipped chat=%s: %s", chat_id, exc)
            return None

        for session in sessions:
            if getattr(session, "session_id", None) == session_id:
                continue
            if getattr(session, "chat_id", None) != chat_id:
                continue
            artifact = getattr(session, "artifact", None)
            if not isinstance(artifact, dict):
                continue
            if artifact.get("kind") not in {"ppt", "docx", "board"}:
                continue
            if str(artifact.get("status") or "").lower() in {"failed", "error"}:
                continue
            if artifact.get("kind") == "ppt" and not artifact.get("download_url"):
                continue
            try:
                return AgentChatArtifact(**artifact)
            except Exception:  # noqa: BLE001
                continue
        return None

    def _looks_like_existing_artifact_update(self, instruction: str) -> bool:
        normalized = instruction.lower()
        if any(keyword in instruction for keyword in ("新建", "重新生成", "再生成一份", "生成一个", "生成一份")):
            return False
        if any(keyword in normalized for keyword in ("create new", "new ppt", "new document", "regenerate")):
            return False
        return any(
            keyword in instruction
            for keyword in (
                "改",
                "修改",
                "调整",
                "优化",
                "详细",
                "丰富",
                "补充",
                "删除",
                "替换",
                "第一页",
                "第二页",
                "第三页",
                "第四页",
                "第五页",
                "第六页",
                "第一张",
                "第二张",
                "第三张",
                "第四张",
                "第五张",
                "第六张",
                "这页",
                "当前",
                "刚才",
                "上一个",
                "继续",
            )
        ) or re.search(r"第\s*\d{1,2}\s*(页|张|p)", instruction) is not None

    async def _run_agent_stream_to_session(self, request: AgentChatRequest) -> None:
        if not hasattr(self._agent_service, "chat_stream_events"):
            await self._agent_service.chat(request)
            return
        streamed_lines: list[str] = []
        try:
            async for event in self._agent_service.chat_stream_events(request):
                if self._sync_service is None:
                    continue
                if not hasattr(self._sync_service, "publish_agent_message"):
                    continue
                content = self._message_from_stream_event(event)
                if content:
                    if streamed_lines and streamed_lines[-1] == content:
                        continue
                    streamed_lines.append(content)
                    await self._sync_service.publish_agent_message(
                        request.session_id,
                        role="assistant",
                        content="\n\n".join(streamed_lines),
                        replace_last=len(streamed_lines) > 1,
                        persist=False,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Feishu agent stream failed session=%s", request.session_id)
            if self._sync_service is not None and hasattr(self._sync_service, "publish_agent_message"):
                await self._sync_service.publish_agent_message(
                    request.session_id,
                    role="assistant",
                    content=f"执行失败：{exc}",
                )

    def _message_from_stream_event(self, event: dict[str, Any]) -> str | None:
        event_type = event.get("event")
        message = event.get("message")
        channel = event.get("channel")
        visibility = event.get("visibility")
        if event_type == "result.created":
            payload = event.get("payload")
            response = payload.get("response") if isinstance(payload, dict) else None
            if isinstance(response, dict):
                plan = response.get("plan")
                final_output = plan.get("final_output") if isinstance(plan, dict) else None
                if (
                    response.get("intent") == AgentIntent.CHAT.value
                    and response.get("artifact") is None
                    and isinstance(plan, dict)
                    and (
                        plan.get("intent") == "intent_clarification"
                        or plan.get("need_clarification") is True
                        or plan.get("clarification_needed") is True
                        or (isinstance(final_output, dict) and final_output.get("format") == "clarification")
                    )
                ):
                    return None
        if event_type in {"clarification.requested", "result.created", "turn.failed"} and channel in {"chat", "error"}:
            return message if isinstance(message, str) and message.strip() else None
        return None

    def _log_agent_task_result(self, session_id: str, task: asyncio.Task[Any]) -> None:
        try:
            task.result()
        except Exception:
            logger.exception("Feishu background agent task failed session=%s", session_id)

    def _coerce_str(self, value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None
        return None

    def _extract_sender_ids(self, sender: Any) -> dict[str, str | None]:
        if not isinstance(sender, dict):
            return {"open_id": None, "union_id": None}
        sender_id = sender.get("sender_id")
        if not isinstance(sender_id, dict):
            sender_id = {}
        return {
            "open_id": self._coerce_str(sender_id.get("open_id") or sender.get("open_id")),
            "union_id": self._coerce_str(sender_id.get("union_id") or sender.get("union_id")),
        }

    def _build_fast_sender_profile(self, sender: Any) -> dict[str, Any]:
        ids = self._extract_sender_ids(sender)
        profile: dict[str, Any] = {}
        if ids["open_id"]:
            profile["sender_open_id"] = ids["open_id"]
            profile["sender_name"] = ids["open_id"]
        if ids["union_id"]:
            profile["sender_union_id"] = ids["union_id"]
        return profile

    async def _resolve_sender_profile(self, sender: Any) -> dict[str, Any]:
        ids = self._extract_sender_ids(sender)
        profile: dict[str, Any] = {}
        if ids["open_id"]:
            profile["sender_open_id"] = ids["open_id"]
        if ids["union_id"]:
            profile["sender_union_id"] = ids["union_id"]

        try:
            async with AsyncSessionLocal() as session:
                user = await AuthRepository(session).resolve_user_by_feishu_identity(
                    open_id=ids["open_id"],
                    union_id=ids["union_id"],
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Feishu sender account resolution skipped: %s", exc)
            user = None

        if user is not None:
            profile["platform_user_id"] = user.id
            profile["platform_display_name"] = user.display_name or user.name
            if user.avatar_url:
                profile["avatar_url"] = user.avatar_url
        elif ids["open_id"]:
            profile["sender_name"] = ids["open_id"]
        return profile

    def _build_user_message(
        self,
        content: str,
        *,
        timestamp: int | None,
        sender_profile: dict[str, Any] | None,
    ) -> dict[str, Any]:
        message: dict[str, Any] = {
            "role": "user",
            "content": content,
            "timestamp": timestamp,
        }
        if sender_profile:
            message.update(sender_profile)
        return message
