from __future__ import annotations

import json
import re
import time
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
        "componentdiagram",
        "activitydiagram",
        "journey",
        "mindmap",
        "pie",
        "mermaid",
        "@startuml",
        "plantuml",
        "流程图",
        "时序图",
        "类图",
        "er 图",
        "er图",
        "组件图",
        "活动图",
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
        "树图",
        "树状图",
        "树形图",
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
    if "饼图" in message or "pie" in lowered:
        return "pie"
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
    _MIN_CREATE_NOTES_SHAPE_COUNT = 6
    _VISIBILITY_RETRIES = 6
    _VISIBILITY_WAIT_SECONDS = 1.5

    def __init__(
        self,
        feishu_board_client: FeishuBoardClient,
        llm_client: LlmClient | None = None,
    ) -> None:
        self._feishu_board_client = feishu_board_client
        self._llm_client = llm_client or LlmClient()

    def generate(
        self,
        *,
        message: str,
        sharing_url: str,
        whiteboard_id: str | None = None,
    ) -> BoardGenerateResult:
        execution_logs: list[tuple[str, str]] = []
        user_message = _strip_rag_context(message)
        resolved_whiteboard_id = whiteboard_id
        if resolved_whiteboard_id:
            execution_logs.append(("resolving_target", f"使用显式 whiteboard_id={resolved_whiteboard_id}"))
        else:
            target = resolve_board_target_from_sharing_url(sharing_url)
            execution_logs.append(("resolving_target", f"开始解析分享链接: {sharing_url}"))
            resolved_whiteboard_id = target.whiteboard_id
            if resolved_whiteboard_id is None and target.doc_token is not None:
                execution_logs.append(("resolving_target", f"检测到文档链接，开始解析 doc_token={target.doc_token}"))
                resolved_whiteboard_id = self._feishu_board_client.resolve_whiteboard_id_from_document(target.doc_token)
        if resolved_whiteboard_id is None:
            raise ValueError(f"Unable to resolve whiteboard from sharing url: {sharing_url}")
        execution_logs.append(("resolving_target", f"已解析 whiteboard_id={resolved_whiteboard_id}"))
        render_mode = choose_render_mode(user_message)
        execution_logs.append(("planning", f"已选择渲染模式: {render_mode}"))

        if render_mode == "import_diagram":
            embedded = extract_embedded_diagram_source(user_message)
            if embedded is not None:
                syntax, source = embedded
                execution_logs.append(("planning", f"检测到用户提供的 {syntax} 源码，直接导入"))
            else:
                diagram_type = choose_import_diagram_type(user_message)
                syntax = _choose_import_syntax(user_message, diagram_type=diagram_type)
                prompt_bundle = build_import_diagram_prompt(message)
                source = self._complete_with_fallback(
                    system_prompt=prompt_bundle["system"],
                    user_prompt=prompt_bundle["user"],
                    fallback=self._build_stub_import_source(user_message, syntax, diagram_type=diagram_type),
                )
                source = _normalize_diagram_source(source, syntax=syntax)
                if syntax == "mermaid" and diagram_type == "pie" and not source.lstrip().lower().startswith("pie"):
                    source = self._build_stub_import_source(user_message, syntax, diagram_type=diagram_type)
            diagram_type = choose_import_diagram_type(source if embedded is not None else user_message)
            execution_logs.append(("planning", f"导入图表语法={syntax} diagram_type={diagram_type}"))
            execution_logs.append(("rendering", "开始执行 board import"))
            try:
                import_result = self._feishu_board_client.import_diagram(
                    resolved_whiteboard_id,
                    source=source,
                    source_type="content",
                    syntax=syntax,
                    diagram_type=diagram_type,
                    style="board",
                )
                ticket_id = import_result["ticket_id"]
                node_ids: list[str] = []
                execution_logs.append(("rendering", f"已提交图表导入，ticket_id={ticket_id}"))
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"标准图导入失败，未降级为 create-notes，避免生成错误图形: {exc}") from exc
        else:
            ticket_id, node_ids = self._create_notes_on_board(
                whiteboard_id=resolved_whiteboard_id,
                message=message,
                user_message=user_message,
                execution_logs=execution_logs,
            )

        if render_mode == "create_notes":
            self._wait_for_created_nodes_visible(
                whiteboard_id=resolved_whiteboard_id,
                expected_node_ids=node_ids,
                execution_logs=execution_logs,
            )
        execution_logs.append(("exporting_preview", "开始获取画板预览"))
        preview_url = self._feishu_board_client.get_board_image(resolved_whiteboard_id)["preview_url"]
        execution_logs.append(("exporting_preview", "画板预览已生成"))
        return BoardGenerateResult(
            whiteboard_id=resolved_whiteboard_id,
            render_mode=render_mode,
            preview_url=preview_url,
            result_summary=f"{render_mode} completed for {resolved_whiteboard_id}",
            ticket_id=ticket_id,
            node_ids=node_ids,
            deleted_count=0,
            execution_logs=execution_logs,
        )

    def _create_notes_on_board(
        self,
        *,
        whiteboard_id: str,
        message: str,
        user_message: str,
        execution_logs: list[tuple[str, str]],
    ) -> tuple[str | None, list[str]]:
        prompt_bundle = build_create_notes_prompt(message)
        plan_payload = self._complete_with_fallback(
            system_prompt=prompt_bundle["system"],
            user_prompt=prompt_bundle["user"],
            fallback="",
        )
        parsed_plan = parse_create_notes_plan(_extract_json_object(plan_payload))
        if parsed_plan is None:
            plan = normalize_create_notes_plan(fallback_plan_from_message(user_message), user_message)
        else:
            plan = normalize_create_notes_plan(parsed_plan, user_message)
            groups = plan.get("groups")
            if not isinstance(groups, list) or not groups:
                plan = normalize_create_notes_plan(fallback_plan_from_message(user_message), user_message)
        shape_entries, connector_entries = build_create_notes_payload(plan)
        if self._is_sparse_create_notes_plan(shape_entries, plan):
            execution_logs.append(("planning", "LLM 画板计划内容过少，已切换为兜底思路图计划"))
            plan = normalize_create_notes_plan(fallback_plan_from_message(user_message), user_message)
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
        created_node_ids = create_result["node_ids"]
        execution_logs.append(("rendering", f"已创建 {len(created_node_ids)} 个形状节点"))
        self._wait_for_created_nodes_visible(
            whiteboard_id=whiteboard_id,
            expected_node_ids=created_node_ids,
            execution_logs=execution_logs,
        )
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
        if not connector_nodes:
            return None, created_node_ids

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
        return None, node_ids

    def _is_sparse_create_notes_plan(
        self,
        shape_entries: list[dict[str, object]],
        plan: dict[str, object],
    ) -> bool:
        if len(shape_entries) < self._MIN_CREATE_NOTES_SHAPE_COUNT:
            return True
        text_values = json.dumps(plan, ensure_ascii=False)
        sparse_markers = ("根节点", "子节点", "中心主题", "中心节点")
        return any(marker in text_values for marker in sparse_markers) and len(shape_entries) < 8

    def _wait_for_created_nodes_visible(
        self,
        *,
        whiteboard_id: str,
        expected_node_ids: list[str],
        execution_logs: list[tuple[str, str]],
    ) -> None:
        expected_count = max(len(expected_node_ids), self._MIN_CREATE_NOTES_SHAPE_COUNT)
        last_count = 0
        for attempt in range(self._VISIBILITY_RETRIES):
            try:
                raw = self._feishu_board_client.get_board_nodes(whiteboard_id)
            except Exception as exc:  # noqa: BLE001
                if attempt == self._VISIBILITY_RETRIES - 1:
                    raise RuntimeError(f"画板节点写入后仍不可读取: {exc}") from exc
                time.sleep(self._VISIBILITY_WAIT_SECONDS)
                continue
            nodes = raw.get("data", {}).get("nodes", [])
            if isinstance(nodes, dict):
                visible_ids = list(nodes.keys())
            elif isinstance(nodes, list):
                visible_ids = [str(node.get("id")) for node in nodes if isinstance(node, dict) and node.get("id")]
            else:
                visible_ids = []
            last_count = len(visible_ids)
            if last_count >= expected_count:
                execution_logs.append(("rendering", f"已确认画板节点可见，visible_count={last_count}"))
                return
            if attempt < self._VISIBILITY_RETRIES - 1:
                time.sleep(self._VISIBILITY_WAIT_SECONDS)
        raise RuntimeError(f"画板节点写入后数量异常，expected>={expected_count} visible={last_count}")

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

    def _build_stub_import_source(self, message: str, syntax: str, *, diagram_type: str = "auto") -> str:
        if syntax == "mermaid":
            if diagram_type == "pie":
                return "\n".join(
                    [
                        "pie showData",
                        f'title {self._short_chart_title(message)}',
                        '  "场地" : 25',
                        '  "搭建" : 20',
                        '  "媒体和达人" : 18',
                        '  "直播与拍摄" : 10',
                        '  "物料和杂项" : 7',
                    ]
                )
            if diagram_type == "sequence":
                return "\n".join(
                    [
                        "sequenceDiagram",
                        "participant U as 用户",
                        "participant F as 前端",
                        "participant B as 后端",
                        "participant D as 数据库",
                        "U->>F: 输入登录信息",
                        "F->>B: 提交登录请求",
                        "B->>D: 查询用户凭证",
                        "D-->>B: 返回验证结果",
                        "B-->>F: 返回登录结果",
                        "F-->>U: 展示登录状态",
                    ]
                )
            if diagram_type == "mindmap":
                return "\n".join(["mindmap", f"  root(({message[:20] or '主题'}))", "    背景", "    要点", "    行动"])
            if diagram_type == "state":
                return "\n".join(["stateDiagram-v2", "[*] --> 待处理", "待处理 --> 处理中", "处理中 --> 已完成", "已完成 --> [*]"])
            if diagram_type == "class":
                return "\n".join(["classDiagram", "class 用户", "class 前端", "class 后端", "用户 --> 前端", "前端 --> 后端"])
            if diagram_type == "er":
                return "\n".join(["erDiagram", "USER ||--o{ ORDER : creates", "USER {", "  string id", "  string name", "}", "ORDER {", "  string id", "  string status", "}"])
            return "\n".join(
                [
                    "flowchart TD",
                    "A[User Request] --> B[Analyze]",
                    f"B --> C[{message[:20] or 'Generate'}]",
            ]
        )
        if diagram_type == "component":
            return "\n".join(["@startuml", "component \"前端应用\" as Frontend", "component \"后端服务\" as Backend", "database \"数据库\" as DB", "Frontend --> Backend", "Backend --> DB", "@enduml"])
        if diagram_type == "activity":
            return "\n".join(["@startuml", "start", ":提交申请;", ":系统校验;", "if (通过?) then (是)", "  :进入审批;", "else (否)", "  :返回修改;", "endif", "stop", "@enduml"])
        return "\n".join(
            [
                "@startuml",
                "rectangle \"User Request\" as A",
                f"rectangle \"{message[:20] or 'Generate'}\" as B",
                "A --> B",
                "@enduml",
            ]
        )

    def _short_chart_title(self, message: str) -> str:
        normalized = " ".join(message.split())
        normalized = normalized.replace("## 用户需求", "").strip()
        normalized = re.sub(r"^(根据|基于).{0,16}(聊天记录|上下文)", "", normalized).strip()
        normalized = re.sub(r"^(生成|制作|绘制|帮我做个?|帮我生成)", "", normalized).strip()
        normalized = normalized.replace("饼图", "").replace("pie chart", "").replace("pie", "").strip()
        return (normalized or "预算分布")[:24]


def _choose_import_syntax(message: str, *, diagram_type: str) -> str:
    lowered = message.lower()
    if "@startuml" in lowered or "plantuml" in lowered:
        return "plantuml"
    if diagram_type in {"component", "activity"}:
        return "plantuml"
    return "mermaid"


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


def _strip_rag_context(message: str) -> str:
    marker = "\n\n## RAG 知识库资料"
    if marker in message:
        return message.split(marker, 1)[0].strip()
    return message.strip()


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
