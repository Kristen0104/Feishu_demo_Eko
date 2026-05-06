from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


class AgentToolRegistry:
    """Enterprise tool catalog passed to the planner and runtime."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._register_defaults()

    def list_specs(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def _register_defaults(self) -> None:
        for spec in [
            ToolSpec("chat", "普通问答回复", {"message": "string"}),
            ToolSpec("docx", "创建 Markdown 文档", {"instruction": "string", "retrieved_context": "array"}),
            ToolSpec("docx_edit", "修改当前文档", {"instruction": "string", "current_document": "object"}),
            ToolSpec("ppt", "根据用户需求创建或编辑 AI PPT。可指定设计模式：template（模板模式，快速稳定生成）或 free_design（自由设计，更强视觉表现）。如果用户没有明确指定设计模式，你必须在 missing_info 中说明并设置 need_clarification=true，主动询问用户偏好哪种模式。", {"topic": "string", "design_mode": "template|free_design", "retrieved_context": "array"}),
            ToolSpec("ppt_create", "创建新 PPT", {"topic": "string", "page_count": "integer", "design_mode": "string", "retrieved_context": "array"}),
            ToolSpec("ppt_edit", "修改当前 PPT", {"instruction": "string", "current_artifact": "object"}),
            ToolSpec("feishu", "创建或解析飞书文档、画板和分享链接", {"title": "string", "sharing_url": "string"}),
            ToolSpec("board", "创建或修改飞书画板", {"message": "string", "sharing_url": "string", "retrieved_context": "array"}),
            ToolSpec("knowledge_search", "检索项目知识、会话历史和产物摘要", {"query": "string"}),
            ToolSpec("artifact_lookup", "读取当前或历史产物", {"kind": "docx|ppt|board"}),
            ToolSpec("sync", "同步任务状态和产物", {"session_id": "string"}),
        ]:
            self.register(spec)
