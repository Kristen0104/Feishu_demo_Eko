from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from app.board_renderer.create_notes import (
    build_connectors_from_mapping,
    build_create_notes_payload,
    fallback_plan_from_message,
    normalize_create_notes_plan,
    parse_create_notes_plan,
)
from app.board_renderer.prompt import (
    build_create_notes_prompt,
    build_import_diagram_prompt,
)
from app.modules.feishu.board_client import FeishuBoardClient
from app.modules.feishu.board_target import resolve_board_target_from_sharing_url
from app.services.llm_client import LlmClient

RenderMode = Literal["import_diagram", "create_notes"]


class BoardGenerateResult(BaseModel):
    whiteboard_id: str
    render_mode: RenderMode
    preview_url: str
    result_summary: str
    ticket_id: str | None = None
    node_ids: list[str] = Field(default_factory=list)
    deleted_count: int = 0
    execution_logs: list[tuple[str, str]] = Field(default_factory=list)


def choose_render_mode(message: str) -> RenderMode:
    lowered = message.lower()

    import_keywords = (
        "```mermaid",
        "```plantuml",
        "graph td",
        "graph lr",
        "graph bt",
        "graph rl",
        "flowchart",
        "sequencediagram",
        "classdiagram",
        "statediagram",
        "erdiagram",
        "journey",
        "mindmap",
        "pie",
        "mermaid",
        "@startuml",
        "plantuml",
        "流程图",
        "时序图",
        "类图",
        "思维导图",
        "饼图",
        "状态图",
    )
    create_notes_keywords = (
        "架构图",
        "架构",
        "architecture",
        "组织架构图",
        "矩阵",
        "对比",
        "kanban",
        "看板",
        "鱼骨图",
        "柱状图",
        "折线图",
        "精排图",
        "自定义图",
    )

    if any(keyword in lowered for keyword in import_keywords):
        return "import_diagram"
    if any(keyword in lowered for keyword in create_notes_keywords):
        return "create_notes"
    return "create_notes"


def choose_import_diagram_type(message: str) -> str:
    lowered = message.lower()
    if "mindmap" in lowered or "思维导图" in message:
        return "mindmap"
    if "sequencediagram" in lowered or "时序图" in message:
        return "sequence"
    if "stateDiagram".lower() in lowered or "状态图" in message:
        return "state"
    if "classdiagram" in lowered or "类图" in message:
        return "class"
    if "componentdiagram" in lowered or "组件图" in message:
        return "component"
    if "activitydiagram" in lowered or "活动图" in message:
        return "activity"
    if "erdiagram" in lowered or "er 图" in message.lower():
        return "er"
    if "flowchart" in lowered or "流程图" in message:
        return "flowchart"
    return "auto"


class BoardGenerateService:
    def __init__(
        self,
        feishu_board_client: FeishuBoardClient,
        llm_client: LlmClient | None = None,
    ) -> None:
        self._feishu_board_client = feishu_board_client
        self._llm_client = llm_client or LlmClient()

    def generate(self, *, message: str, sharing_url: str) -> BoardGenerateResult:
        execution_logs: list[tuple[str, str]] = []
        target = resolve_board_target_from_sharing_url(sharing_url)
        execution_logs.append(("resolving_target", f"开始解析分享链接: {sharing_url}"))
        whiteboard_id = target.whiteboard_id
        if whiteboard_id is None and target.doc_token is not None:
            execution_logs.append(("resolving_target", f"检测到文档链接，开始解析 doc_token={target.doc_token}"))
            whiteboard_id = self._feishu_board_client.resolve_whiteboard_id_from_document(target.doc_token)
        if whiteboard_id is None:
            raise ValueError(f"Unable to resolve whiteboard from sharing url: {sharing_url}")
        execution_logs.append(("resolving_target", f"已解析 whiteboard_id={whiteboard_id}"))
        render_mode = choose_render_mode(message)
        execution_logs.append(("planning", f"已选择渲染模式: {render_mode}"))

        if render_mode == "import_diagram":
            embedded = extract_embedded_diagram_source(message)
            if embedded is not None:
                syntax, source = embedded
                execution_logs.append(("planning", f"检测到用户提供的 {syntax} 源码，直接导入"))
            else:
                syntax = "mermaid" if "graph " in message.lower() or "mermaid" in message.lower() else "plantuml"
                prompt_bundle = build_import_diagram_prompt(message)
                source = self._complete_with_fallback(
                    system_prompt=prompt_bundle["system"],
                    user_prompt=prompt_bundle["user"],
                    fallback=self._build_stub_import_source(message, syntax),
                )
                source = _normalize_diagram_source(source, syntax=syntax)
            diagram_type = choose_import_diagram_type(source if embedded is not None else message)
            execution_logs.append(("planning", f"导入图表语法={syntax} diagram_type={diagram_type}"))
            execution_logs.append(("rendering", "开始执行 board import"))
            import_result = self._feishu_board_client.import_diagram(
                whiteboard_id,
                source=source,
                source_type="content",
                syntax=syntax,
                diagram_type=diagram_type,
                style="board",
            )
            ticket_id = import_result["ticket_id"]
            node_ids: list[str] = []
            execution_logs.append(("rendering", f"已提交图表导入，ticket_id={ticket_id}"))
        else:
            prompt_bundle = build_create_notes_prompt(message)
            plan_payload = self._complete_with_fallback(
                system_prompt=prompt_bundle["system"],
                user_prompt=prompt_bundle["user"],
                fallback="",
            )
            parsed_plan = parse_create_notes_plan(_extract_json_object(plan_payload))
            if parsed_plan is None:
                plan = normalize_create_notes_plan(fallback_plan_from_message(message), message)
            else:
                plan = normalize_create_notes_plan(parsed_plan, message)
                groups = plan.get("groups")
                if not isinstance(groups, list) or not groups:
                    plan = normalize_create_notes_plan(fallback_plan_from_message(message), message)
            shape_entries, connector_entries = build_create_notes_payload(plan)
            shape_nodes = [entry["node"] for entry in shape_entries]
            execution_logs.append(("planning", f"已生成 create-notes 计划，shape_count={len(shape_nodes)} connector_count={len(connector_entries)}"))
            execution_logs.append(("rendering", "开始创建形状节点"))
            create_result = self._feishu_board_client.create_notes(
                whiteboard_id,
                nodes_json_or_nodes=shape_nodes,
                source_type="content",
                client_token="",
                user_id_type="open_id",
            )
            ticket_id = None
            created_node_ids = create_result["node_ids"]
            execution_logs.append(("rendering", f"已创建 {len(created_node_ids)} 个形状节点"))
            key_to_node_id = {
                entry["key"]: created_node_ids[index]
                for index, entry in enumerate(shape_entries)
                if index < len(created_node_ids)
            }
            connector_nodes = build_connectors_from_mapping(
                connector_entries,
                key_to_node_id,
                palette=str(plan.get("palette") or "classic"),
            )
            if connector_nodes:
                execution_logs.append(("rendering", f"开始创建 {len(connector_nodes)} 条连接线"))
                connector_result = self._feishu_board_client.create_notes(
                    whiteboard_id,
                    nodes_json_or_nodes=connector_nodes,
                    source_type="content",
                    client_token="",
                    user_id_type="open_id",
                )
                node_ids = created_node_ids + connector_result["node_ids"]
                execution_logs.append(("rendering", f"已创建 {len(connector_result['node_ids'])} 条连接线"))
            else:
                node_ids = created_node_ids

        execution_logs.append(("exporting_preview", "开始获取画板预览"))
        preview_url = self._feishu_board_client.get_board_image(whiteboard_id)["preview_url"]
        execution_logs.append(("exporting_preview", "画板预览已生成"))
        return BoardGenerateResult(
            whiteboard_id=whiteboard_id,
            render_mode=render_mode,
            preview_url=preview_url,
            result_summary=f"{render_mode} completed for {whiteboard_id}",
            ticket_id=ticket_id,
            node_ids=node_ids,
            deleted_count=0,
            execution_logs=execution_logs,
        )

    def _complete_with_fallback(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        fallback: str,
    ) -> str:
        if not self._llm_client.is_configured():
            return fallback
        try:
            return self._llm_client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception:
            return fallback

    def _build_stub_import_source(self, message: str, syntax: str) -> str:
        if syntax == "mermaid":
            return "\n".join(
                [
                    "flowchart TD",
                    "A[User Request] --> B[Analyze]",
                    f"B --> C[{message[:20] or 'Generate'}]",
                ]
            )
        return "\n".join(
            [
                "@startuml",
                "rectangle \"User Request\" as A",
                f"rectangle \"{message[:20] or 'Generate'}\" as B",
                "A --> B",
                "@enduml",
            ]
        )


def extract_embedded_diagram_source(message: str) -> tuple[str, str] | None:
    fenced = re.search(r"```(mermaid|plantuml)\s*(.*?)```", message, re.IGNORECASE | re.DOTALL)
    if fenced:
        syntax = fenced.group(1).lower()
        source = fenced.group(2).strip()
        return syntax, source

    if "@startuml" in message.lower():
        start = message.lower().find("@startuml")
        end = message.lower().rfind("@enduml")
        if end != -1 and end > start:
            source = message[start:end + len("@enduml")].strip()
            return "plantuml", source

    mermaid_leads = ("graph ", "flowchart ", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram", "mindmap", "pie ")
    stripped = message.strip()
    if any(stripped.startswith(prefix) for prefix in mermaid_leads):
        return "mermaid", stripped

    return None


def _normalize_diagram_source(source: str, *, syntax: str) -> str:
    stripped = source.strip()
    fenced = re.fullmatch(r"```(?:mermaid|plantuml)?\s*(.*?)```", stripped, re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()

    if syntax == "plantuml" and "@startuml" not in stripped.lower():
        return "\n".join(["@startuml", stripped, "@enduml"])
    return stripped


def _extract_json_object(content: str) -> str:
    stripped = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(stripped)):
            char = stripped[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = stripped[start:index + 1]
                    try:
                        json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    return candidate
        start = stripped.find("{", start + 1)
    return content
