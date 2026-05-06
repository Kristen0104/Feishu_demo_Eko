from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any

try:
    from lark_oapi.core.utils import AESCipher
except ImportError:  # pragma: no cover - optional dependency for encrypted events
    AESCipher = None

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.modules.agent.schemas import AgentChatArtifact, AgentChatRequest, AgentContext, ChatMessage
from app.modules.auth.repository import AuthRepository
from app.modules.feishu.service import FeishuService
from app.modules.sync.service import SyncService

if TYPE_CHECKING:
    from app.modules.agent.service import AgentService

logger = logging.getLogger(__name__)
_MENTION_TAG_RE = re.compile(r"<at[^>]*>.*?</at>", re.IGNORECASE | re.DOTALL)


class FeishuEventProcessor:
    def __init__(
        self,
        feishu_service: FeishuService,
        agent_service: AgentService,
        sync_service: SyncService | None = None,
    ) -> None:
        self._feishu_service = feishu_service
        self._agent_service = agent_service
        self._sync_service = sync_service

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
                    messages=[trigger_message],
                )
                logger.info(
                    "Feishu direct mention opened session=%s before loading context",
                    session_id,
                )
                await self._sync_service.publish_agent_message(
                    session_id,
                    role="assistant",
                    content="收到。我先理解你的任务，并拆成可以执行的步骤。",
                )
            self._schedule_new_session_bootstrap(
                session_id=session_id,
                chat_id=chat_id,
                before_time_ms=create_time,
                instruction=instruction,
                sender_profile=sender_profile,
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

        if token is not None and token != expected:
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
        if not isinstance(mentions, list) or not mentions:
            return False

        app_id = settings.FEISHU_APP_ID.strip() if isinstance(settings.FEISHU_APP_ID, str) else ""
        if not app_id:
            return False

        for mention in mentions:
            if not isinstance(mention, dict):
                continue
            if mention.get("id_type") == "app_id" and mention.get("id") == app_id:
                return True
        return False

    @staticmethod
    def message_mentions_app(message: dict[str, Any], app_id: str) -> bool:
        if not app_id:
            return False
        mentions = message.get("mentions")
        if not isinstance(mentions, list):
            return False
        for mention in mentions:
            if not isinstance(mention, dict):
                continue
            if mention.get("id_type") == "app_id" and mention.get("id") == app_id:
                return True
        return False

    def _extract_command_text(self, message: dict[str, Any]) -> str:
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

        request = AgentChatRequest(
            session_id=session_id,
            message=instruction,
            context=AgentContext(chat_history=[]),
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

    async def _bootstrap_new_session(
        self,
        *,
        session_id: str,
        chat_id: str,
        before_time_ms: int | None,
        instruction: str,
        sender_profile: dict[str, Any] | None,
    ) -> None:
        try:
            context_candidates = await asyncio.to_thread(
                self._feishu_service.get_chat_context_candidates,
                chat_id,
                before_time_ms=before_time_ms,
                limit=50,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Feishu context fetch failed; continuing with empty context session=%s chat=%s: %s",
                session_id,
                chat_id,
                exc,
            )
            context_candidates = []
        if self._sync_service is not None:
            await self._sync_service.update_session_context(
                session_id,
                context_size=len(context_candidates),
                context_messages=context_candidates,
            )
            logger.info(
                "Feishu direct mention loaded session=%s with %s context candidates",
                session_id,
                len(context_candidates),
            )
        current_artifact = await self._resolve_current_artifact_for_followup(chat_id, session_id, instruction)
        request = AgentChatRequest(
            session_id=session_id,
            message=instruction,
            current_document=current_artifact,
            context=AgentContext(
                chat_history=[
                    ChatMessage(
                        role=str(message.get("role") or "user"),
                        content=str(message.get("content") or ""),
                        timestamp=self._coerce_int(message.get("timestamp")),
                        sender_open_id=self._coerce_str(message.get("sender_open_id")),
                        sender_union_id=self._coerce_str(message.get("sender_union_id")),
                        sender_name=self._coerce_str(message.get("sender_name")),
                        platform_user_id=self._coerce_str(message.get("platform_user_id")),
                        platform_display_name=self._coerce_str(message.get("platform_display_name")),
                        avatar_url=self._coerce_str(message.get("avatar_url")),
                    )
                    for message in context_candidates
                    if str(message.get("content") or "").strip()
                ]
            ),
            sender=sender_profile,
        )
        await self._run_agent_stream_to_session(request)

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
        if event_type in {
            "turn.started",
            "intent.recognized",
            "context.loaded",
            "retrieval.started",
            "retrieval.completed",
            "plan.created",
            "plan.summary",
            "plan.step",
            "tool.selected",
            "tool.started",
            "tool.completed",
            "clarification.requested",
            "result.created",
            "turn.failed",
        }:
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
