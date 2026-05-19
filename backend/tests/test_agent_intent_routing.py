from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from app.modules.agent.schemas import AgentIntent
from app.modules.agent.service import AgentService, RouterAgent


class _LLMReturnsChat:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"chat","intent":"chat","confidence":0.99,"reason":"仅输入主题"}'


class _LLMReturnsDocx:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"docx","intent":"docx","confidence":0.99,"reason":"策略文档"}'


class _LLMReturnsBoard:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"board","intent":"board","confidence":0.99,"reason":"生成时序图"}'


class _LLMReturnsLowConfidence:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"docx","intent":"docx","confidence":0.2,"reason":"不确定"}'


class _LLMReturnsVagueDocx:
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return '{"primary_tool":"docx","intent":"docx","confidence":0.82,"reason":"整理请求"}'


class _LLMTracksCalls:
    def __init__(self, result: str) -> None:
        self.result = result
        self.calls = 0

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        self.calls += 1
        return self.result


class AgentIntentRoutingTest(IsolatedAsyncioTestCase):
    async def test_bare_strategy_topic_stays_chat_not_docx(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        intent = await router.classify_chat_intent("NovaMind 模型分级策略")

        self.assertEqual(intent, AgentIntent.CHAT)

    async def test_bare_strategy_topic_routes_as_clean_topic_discussion(self) -> None:
        llm = _LLMTracksCalls('{"primary_tool":"docx","intent":"docx","confidence":0.99,"reason":"策略文档"}')
        router = RouterAgent(llm)

        route = await router.route_chat_intent("NovaMind 模型分级策略")

        self.assertEqual(llm.calls, 1)
        self.assertEqual(route.intent, "chat")
        self.assertEqual(route.primary_tool, "chat")
        self.assertFalse(route.needs_clarification)
        self.assertEqual(route.reason, "策略文档")
        self.assertEqual([candidate.tool for candidate in route.candidates], ["docx", "chat"])

    async def test_bare_strategy_topic_stays_chat_even_if_model_selects_docx(self) -> None:
        router = RouterAgent(_LLMReturnsDocx())

        intent = await router.classify_chat_intent("NovaMind 模型分级策略")

        self.assertEqual(intent, AgentIntent.CHAT)

    async def test_sequence_diagram_request_uses_model_board_intent(self) -> None:
        router = RouterAgent(_LLMReturnsBoard())

        intent = await router.classify_chat_intent("根据聊天记录生成时序图")

        self.assertEqual(intent, AgentIntent.BOARD)

    async def test_explicit_ppt_generation_uses_local_ppt_intent_even_if_model_selects_chat(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        intent = await router.classify_chat_intent("生成舞蹈ppt")

        self.assertEqual(intent, AgentIntent.PPT)

    async def test_chart_generation_uses_local_board_intent_even_if_model_selects_chat(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        for message in ["生成一个测试饼图", "帮我做个销售柱状图", "draw a line chart"]:
            with self.subTest(message=message):
                intent = await router.classify_chat_intent(message)

                self.assertEqual(intent, AgentIntent.BOARD)

    async def test_low_confidence_route_requests_clarification(self) -> None:
        router = RouterAgent(_LLMReturnsLowConfidence())

        route = await router.route_chat_intent("帮我处理一下这个")

        self.assertTrue(route.needs_clarification)
        self.assertIn("直接讨论", [option.label for option in route.clarification_options])
        self.assertIn("生成文档", [option.label for option in route.clarification_options])

    async def test_vague_organize_request_uses_model_score_for_clarification(self) -> None:
        router = RouterAgent(_LLMReturnsVagueDocx())

        route = await router.route_chat_intent("整理一下吧")

        self.assertTrue(route.needs_clarification)
        self.assertEqual(route.reason, "办公动作不完整")
        self.assertIn("生成文档", [option.label for option in route.clarification_options])

    async def test_vague_organize_request_clarifies_even_when_model_selects_chat(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        route = await router.route_chat_intent("整理一下")

        self.assertTrue(route.needs_clarification)
        self.assertEqual(route.reason, "办公动作不完整")

    async def test_explicit_ppt_route_does_not_request_clarification(self) -> None:
        router = RouterAgent(_LLMReturnsChat())

        route = await router.route_chat_intent("生成舞蹈ppt")

        self.assertFalse(route.needs_clarification)
        self.assertEqual(route.intent, "ppt")

    async def test_current_artifact_vague_edit_requests_clarification(self) -> None:
        from app.modules.agent.schemas import AgentChatArtifact

        router = RouterAgent(_LLMReturnsChat())

        route = await router.route_chat_intent(
            "帮我整理一下这个",
            current_artifact=AgentChatArtifact(kind="ppt", job_id="job_test"),
        )

        self.assertTrue(route.needs_clarification)
        self.assertIn("修改当前PPT", [option.label for option in route.clarification_options])


class _SyncSession:
    route_state = {
        "state": "awaiting_clarification",
        "clarification_type": "intent_route",
        "original_message": "NovaMind 模型分级策略",
    }
    messages = [
        {"role": "user", "content": "NovaMind 模型分级策略"},
        {"role": "assistant", "content": "你是想直接讨论这个主题，还是生成一份文档、PPT 或画板？"},
    ]


class _SyncService:
    def __init__(self, session: object | None = None) -> None:
        self.session = session or _SyncSession()
        self.route_state_updates: list[dict[str, object] | None] = []
        self.completed_payloads: list[dict[str, object]] = []

    async def get_session(self, _session_id: str) -> _SyncSession:
        return self.session

    async def update_session_route_state(self, _session_id: str, route_state: dict[str, object] | None) -> None:
        self.route_state_updates.append(route_state)

    async def publish_task_completed(self, _session_id: str, **payload: object) -> None:
        self.completed_payloads.append(payload)


class AgentPendingRouteReplyTest(IsolatedAsyncioTestCase):
    async def test_clarification_reply_restores_original_message_and_forces_intent(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest

        service = AgentService.__new__(AgentService)
        service._sync_service = _SyncService()

        request = await service._resolve_pending_route_reply(
            AgentChatRequest(session_id="s1", message="生成文档")
        )

        self.assertEqual(request.message, "NovaMind 模型分级策略")
        self.assertEqual(request.forced_intent, "docx")
        self.assertEqual(service._sync_service.route_state_updates, [None])

    async def test_non_selection_reply_stays_blocked_on_clarification(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest

        service = AgentService.__new__(AgentService)
        service._sync_service = _SyncService()

        request = await service._resolve_pending_route_reply(
            AgentChatRequest(session_id="s1", message="整理一下")
        )

        self.assertEqual(request.message, "整理一下")
        self.assertEqual(request.forced_intent, "chat")
        self.assertEqual(request.sender, {"pending_clarification": True})

    async def test_pending_clarification_reuses_last_question(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest

        service = AgentService.__new__(AgentService)
        class _LegacySession:
            route_state = None
            messages = _SyncSession.messages

        service._sync_service = _SyncService(_LegacySession())

        response = await service._pending_clarification_response(
            AgentChatRequest(
                session_id="s1",
                message="整理一下",
                sender={"pending_clarification": True},
                forced_intent="chat",
            )
        )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.intent, "chat")
        self.assertIn("直接讨论", response.message)

    async def test_structured_clarification_reply_collects_slots_without_message_matching(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest

        class _StructuredSession:
            route_state = {
                "state": "awaiting_clarification",
                "clarification_type": "organize_request",
                "original_message": "整理一下",
                "slots": {},
                "required_slots": ["content_scope", "output_format"],
                "options": {
                    "content_scope": ["recent_chat", "other_information"],
                    "output_format": ["summary", "bullet_list", "minutes", "document"],
                },
            }
            messages = []

        sync = _SyncService(_StructuredSession())
        service = AgentService.__new__(AgentService)
        service._sync_service = sync

        request = await service._resolve_pending_route_reply(
            AgentChatRequest(session_id="s1", message="对话记录")
        )
        response = await service._pending_clarification_response(
            request.model_copy(update={"sender": {"pending_clarification": True}})
        )

        self.assertEqual(request.forced_intent, "chat")
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("整理成什么形式", response.message)
        self.assertEqual(sync.route_state_updates[-1]["slots"], {"content_scope": "recent_chat"})

    async def test_publishing_pending_clarification_does_not_clear_route_state(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest, AgentChatResponse

        sync = _SyncService()
        service = AgentService.__new__(AgentService)
        service._sync_service = sync

        async def _noop_echo(*args: object, **kwargs: object) -> None:
            return None

        async def _empty_messages(*args: object, **kwargs: object) -> list[dict[str, object]]:
            return []

        service._echo_feishu_chat_reply_if_needed = _noop_echo
        service._build_merged_sync_messages = _empty_messages

        await service._publish_chat_result(
            AgentChatRequest(
                session_id="s1",
                message="刚才的对话记录吧",
                sender={"pending_clarification": True},
            ),
            AgentChatResponse(
                session_id="s1",
                intent="chat",
                status="completed",
                message="好的，我会整理你指定的内容。你希望整理成什么形式？",
            ),
        )

        self.assertEqual(sync.route_state_updates, [])

    async def test_publishing_runtime_clarification_does_not_clear_route_state(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest, AgentChatResponse, AgentEventV1

        sync = _SyncService()
        service = AgentService.__new__(AgentService)
        service._sync_service = sync

        async def _noop_echo(*args: object, **kwargs: object) -> None:
            return None

        async def _empty_messages(*args: object, **kwargs: object) -> list[dict[str, object]]:
            return []

        service._echo_feishu_chat_reply_if_needed = _noop_echo
        service._build_merged_sync_messages = _empty_messages

        await service._publish_chat_result(
            AgentChatRequest(session_id="s1", message="整理一下吧"),
            AgentChatResponse(
                session_id="s1",
                intent="chat",
                status="completed",
                message="你是想直接讨论这个主题，还是生成一份文档、PPT 或画板？",
                events=[
                    AgentEventV1(
                        event="clarification.requested",
                        status="blocked",
                        channel="chat",
                        visibility="user",
                        message="你是想直接讨论这个主题，还是生成一份文档、PPT 或画板？",
                    )
                ],
            ),
        )

        self.assertEqual(sync.route_state_updates, [])

    async def test_runtime_clarification_persists_route_state(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest, IntentCandidate, IntentClarificationOption, IntentRouteResult

        class _Turn:
            clarification_requested = True
            trace_events = []
            route_result = IntentRouteResult(
                intent="chat",
                primary_tool="chat",
                confidence=0.4,
                reason="办公动作不完整",
                candidates=[
                    IntentCandidate(intent="docx", tool="docx", confidence=0.82, reason="整理请求"),
                    IntentCandidate(intent="chat", tool="chat", confidence=0.45, reason="可直接讨论"),
                ],
                clarification_options=[
                    IntentClarificationOption(label="直接讨论", intent="chat", tool="chat"),
                    IntentClarificationOption(label="生成文档", intent="docx", tool="docx"),
                ],
                pending_route={"original_message": "整理一下吧", "reason": "办公动作不完整"},
            )

        sync = _SyncService()
        service = AgentService.__new__(AgentService)
        service._sync_service = sync

        await service._persist_runtime_clarification_route(
            AgentChatRequest(session_id="s1", message="整理一下吧"),
            _Turn(),
        )

        self.assertEqual(sync.route_state_updates[0]["state"], "awaiting_clarification")
        self.assertEqual(sync.route_state_updates[0]["clarification_type"], "intent_route")
        self.assertEqual(sync.route_state_updates[0]["original_message"], "整理一下吧")
        self.assertEqual(sync.route_state_updates[0]["reason"], "办公动作不完整")
        self.assertEqual(sync.route_state_updates[0]["options"][1]["intent"], "docx")


class AgentTopicDiscussionPromptTest(IsolatedAsyncioTestCase):
    async def test_topic_discussion_prompt_stays_clean(self) -> None:
        from app.modules.agent.schemas import AgentChatRequest, IntentRouteResult

        service = AgentService.__new__(AgentService)

        prompt = service._build_chat_prompt(
            AgentChatRequest(session_id="s1", message="NovaMind 模型分级策略"),
            route_result=IntentRouteResult(
                intent="chat",
                primary_tool="chat",
                confidence=0.95,
                reason="topic_discussion",
            ),
        )

        self.assertIn("用户只给了一个主题或议题", prompt)
        self.assertIn("不要询问是否生成文档、PPT 或画板", prompt)

    async def test_chat_reply_cleanup_removes_internal_progress_lines(self) -> None:
        service = AgentService.__new__(AgentService)

        cleaned = service._clean_chat_reply(
            "收到。我先理解你的任务，并拆成可以执行的步骤。\n\n"
            "我判断这次要走 chat 能力。\n\n"
            "开始检索相关知识、历史上下文和当前产物。\n\n"
            "规划完成。下面按这些子任务执行。\n\n"
            "直接回答用户问题。\n\n"
            "1. 生成回复\n\n"
            "好的，我现在直接回复这个问题。\n\n"
            "这是最终回答。"
        )

        self.assertEqual(cleaned, "这是最终回答。")
