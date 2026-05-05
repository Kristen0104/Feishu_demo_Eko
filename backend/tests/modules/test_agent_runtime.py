from __future__ import annotations

import asyncio

from app.modules.agent.planner import PlannerAgent
from app.modules.agent.runtime import AgentRuntime
from app.modules.agent.schemas import AgentChatRequest, AgentContext, AgentIntent, KnowledgeDoc
from app.modules.agent.tools import AgentToolRegistry


class PlanningLLMClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        return """
        {
          "goal": "生成动漫发展 PPT",
          "intent": "ppt_generation",
          "task_complexity": "medium",
          "missing_info": ["生成模式"],
          "need_clarification": true,
          "questions": ["你希望用模板模式还是自由设计？"],
          "assumptions": ["默认先不创建 PPT，等用户确认模式"],
          "summary": "先理解 PPT 主题，再确认生成模式。",
          "visible_summary": "我理解你要生成一份动漫发展 PPT，需要先确认模板模式还是自由设计。",
          "tool_candidates": ["knowledge_search", "ppt_create"],
          "steps": [
            {
              "id": "step_1",
              "title": "理解展示需求",
              "description": "识别 PPT 主题和目标",
              "type": "reasoning",
              "tool": null,
              "input": {},
              "expected_output": "明确展示目标",
              "depends_on": []
            },
            {
              "id": "step_2",
              "title": "确认生成模式",
              "description": "追问模板模式或自由设计",
              "type": "clarification",
              "tool": null,
              "input": {},
              "expected_output": "用户确认模式",
              "depends_on": ["step_1"]
            }
          ],
          "final_output": {"format": "ppt_file", "requirements": ["可预览", "可下载"]}
        }
        """


class DocxPlanningLLMClient(PlanningLLMClient):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt))
        return """
        {
          "goal": "写一份活动方案",
          "intent": "doc_generation",
          "task_complexity": "medium",
          "missing_info": [],
          "need_clarification": false,
          "questions": [],
          "assumptions": [],
          "summary": "生成活动方案文档。",
          "visible_summary": "我理解你要写一份活动方案。我会先规划结构，再调用文档工具生成内容。",
          "tool_candidates": ["docx"],
          "steps": [
            {
              "id": "step_1",
              "title": "生成文档",
              "description": "调用文档工具生成活动方案",
              "type": "tool_call",
              "tool": "docx",
              "input": {"instruction": "写一份活动方案"},
              "expected_output": "Markdown 文档",
              "depends_on": []
            }
          ],
          "final_output": {"format": "markdown_document", "requirements": ["结构清晰"]}
        }
        """


def test_planner_outputs_visible_summary_tool_candidates_and_step_status() -> None:
    planner = PlannerAgent(PlanningLLMClient())  # type: ignore[arg-type]

    plan = asyncio.run(
        planner.create_plan(
            "生成动漫发展 PPT",
            routed_intent=AgentIntent.PPT,
            context=None,
        )
    )

    assert plan.visible_summary == "我理解你要生成一份动漫发展 PPT，需要先确认模板模式还是自由设计。"
    assert plan.tool_candidates == ["knowledge_search", "ppt_create"]
    assert [step.status for step in plan.steps] == ["pending", "pending"]


def test_runtime_prepares_turn_with_retrieval_and_trace_events() -> None:
    llm = PlanningLLMClient()
    runtime = AgentRuntime(planner=PlannerAgent(llm))  # type: ignore[arg-type]
    request = AgentChatRequest(
        session_id="s1",
        message="生成动漫发展 PPT",
        context=AgentContext(
            knowledge_docs=[
                KnowledgeDoc(
                    title="动漫产业资料",
                    content="动漫行业正在向 IP 化、全球发行和衍生品联动发展。",
                    source="knowledge://anime",
                )
            ]
        ),
    )

    state = asyncio.run(
        runtime.prepare_turn(
            request,
            routed_intent=AgentIntent.PPT,
            current_artifact=None,
        )
    )

    assert state.plan is not None
    assert state.plan.visible_summary.startswith("我理解你要生成")
    assert state.retrieved_context[0].title == "动漫产业资料"
    assert [event.type for event in state.trace_events] == [
        "turn_started",
        "context_loaded",
        "retrieval_started",
        "retrieval_completed",
        "plan_created",
    ]
    retrieval_event = next(event for event in state.trace_events if event.type == "retrieval_completed")
    assert retrieval_event.data["sources"][0]["source_id"] == "knowledge://anime"
    assert retrieval_event.data["sources"][0]["title"] == "动漫产业资料"
    assert state.trace_events[-1].status == "completed"
    planner_prompt = llm.calls[-1][1]
    assert "knowledge_search" in planner_prompt
    assert "动漫产业资料" in planner_prompt


def test_runtime_executes_registered_langchain_tool_from_plan() -> None:
    captured_context: list[dict] = []

    async def docx_tool(
        instruction: str,
        session_id: str | None = None,
        retrieved_context: list[dict] | None = None,
    ) -> dict[str, str]:
        captured_context.extend(retrieved_context or [])
        return {"content": f"# 活动方案\n\n{instruction}"}

    runtime = AgentRuntime(
        planner=PlannerAgent(DocxPlanningLLMClient()),  # type: ignore[arg-type]
        tool_handlers={"docx": docx_tool},
    )

    state = asyncio.run(
        runtime.prepare_turn(
            AgentChatRequest(
                session_id="s1",
                message="写一份活动方案",
                context=AgentContext(
                    knowledge_docs=[
                        KnowledgeDoc(
                            title="活动知识库",
                            content="活动方案必须包含背景、目标与执行节奏。",
                            source="knowledge://activity",
                        )
                    ]
                ),
            ),
            routed_intent=AgentIntent.DOCX,
            current_artifact=None,
            execute_tools=True,
        )
    )

    assert state.selected_tool == "docx"
    assert state.tool_results == [{"tool": "docx", "result": {"content": "# 活动方案\n\n写一份活动方案"}}]
    assert captured_context[0]["title"] == "活动知识库"
    assert "执行节奏" in captured_context[0]["content"]
    assert [event.type for event in state.trace_events][-3:] == [
        "tool_selected",
        "tool_started",
        "tool_completed",
    ]


def test_fallback_plan_tools_are_registered() -> None:
    planner = PlannerAgent(PlanningLLMClient())  # type: ignore[arg-type]
    registry = AgentToolRegistry()
    registered_tools = set(registry.names())

    for intent in [AgentIntent.DOCX, AgentIntent.PPT, AgentIntent.BOARD, AgentIntent.CHAT]:
        plan = planner._fallback_plan("测试任务", intent)
        plan_tools = {step.tool for step in plan.steps if step.tool}
        assert plan_tools <= registered_tools
        assert set(plan.tool_candidates) <= registered_tools
