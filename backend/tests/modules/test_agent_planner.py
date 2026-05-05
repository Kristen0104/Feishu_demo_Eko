from __future__ import annotations

import asyncio

from app.modules.agent.planner import PlannerAgent
from app.modules.agent.schemas import AgentIntent


class FakePlannerLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str, float]] = []

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        self.calls.append((system_prompt, user_prompt, temperature))
        return self.response


def test_planner_parses_structured_task_plan() -> None:
    llm = FakePlannerLLM(
        """
        ```json
        {
          "goal": "生成项目汇报 PPT",
          "intent": "ppt_generation",
          "task_complexity": "medium",
          "missing_info": [],
          "need_clarification": false,
          "assumptions": ["默认生成商务汇报"],
          "summary": "整理上下文并创建 PPT 任务",
          "steps": [
            {
              "id": "step_1",
              "title": "梳理主题",
              "description": "提取汇报主题和页数要求",
              "type": "reasoning",
              "tool": null,
              "input": {"page_count": 6},
              "expected_output": "PPT 需求",
              "depends_on": []
            },
            {
              "id": "step_2",
              "title": "生成 PPT",
              "description": "调用 AI PPT 服务创建生成任务",
              "type": "tool_call",
              "tool": "ppt",
              "input": {},
              "expected_output": "PPT 生成任务",
              "depends_on": ["step_1"]
            }
          ],
          "final_output": {
            "format": "ppt_file",
            "requirements": ["可下载"]
          }
        }
        ```
        """
    )
    planner = PlannerAgent(llm)

    plan = asyncio.run(planner.create_plan("帮我生成项目汇报 PPT", routed_intent=AgentIntent.PPT))

    assert plan.goal == "生成项目汇报 PPT"
    assert plan.intent == "ppt_generation"
    assert plan.task_complexity == "medium"
    assert [step.tool for step in plan.steps] == [None, "ppt"]
    assert plan.steps[0].type == "reasoning"
    assert plan.steps[1].expected_output == "PPT 生成任务"
    assert plan.steps[1].depends_on == ["step_1"]
    assert plan.final_output.format == "ppt_file"
    assert llm.calls[0][2] == 0.0


def test_planner_falls_back_to_deterministic_steps_when_llm_plan_is_invalid() -> None:
    planner = PlannerAgent(FakePlannerLLM("不是 JSON"))

    plan = asyncio.run(planner.create_plan("把这个流程画到飞书画板", routed_intent=AgentIntent.BOARD))

    assert plan.intent == "board_generation"
    assert plan.goal == "把这个流程画到飞书画板"
    assert [step.tool for step in plan.steps] == ["feishu", "board", "sync"]
    assert plan.steps[1].title == "生成并写入画板"
    assert plan.steps[1].type == "tool_call"
