from __future__ import annotations

from app.board_renderer.create_notes import CREATE_NOTES_RULE_SUMMARY


def build_import_diagram_prompt(message: str) -> dict[str, str]:
    system = "\n".join(
        [
            "You are a Feishu board diagram generator.",
            "Follow the feishu-cli board import route.",
            "Prefer Mermaid for flowcharts, sequence diagrams, class diagrams, mindmaps, pie charts, and similar auto-layout diagrams.",
            "If the user already provided Mermaid or PlantUML, preserve the same syntax family and return only the cleaned source.",
            "Return only diagram source text, with no markdown fences and no explanation.",
        ]
    )
    return {"system": system, "user": message}


def build_create_notes_prompt(message: str) -> dict[str, str]:
    system = "\n".join(
        [
            "You are a Feishu board planner for create-notes rendering.",
            "Follow the feishu-cli board create-notes route.",
            CREATE_NOTES_RULE_SUMMARY,
            "User-specified colors or style always win. If the user does not specify a theme, use the classic palette.",
            "Match information density to user intent: simple request -> 3 layers with 2-3 nodes each, normal request -> 3-4 layers with 3-4 nodes each, detailed request -> 4-5 layers with 4-6 nodes each.",
            "For organization charts, use 3-4 layers and keep each parent at 2-4 children. If one row would exceed 5 nodes, split into child groups instead of forcing one wide row.",
            "When the prompt is short or vague, supplement with reasonable domain content instead of repeating only literal words.",
            "Keep each node text short: title plus one brief explanation line.",
            "Apply connector budgets exactly: <=8 edges draw all, 9-15 edges keep representative edges, >15 edges simplify to layer-to-layer or reduce nodes.",
            "Estimate node size from text length and line count, and left-align longer or multi-line content.",
            'Return only compact JSON. Example: {"title":"AI 网关架构图","palette":"classic","layout":"layered","groups":[{"title":"接入层","nodes":["Web 应用\\n用户入口","开放接口\\n外部接入"]}],"edges":[{"from":"g0n0","to":"g1n0","direction":"tb"}]}',
        ]
    )
    return {"system": system, "user": message}
