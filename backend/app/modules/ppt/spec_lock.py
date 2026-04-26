from __future__ import annotations

from .models import DeckPlan


def render_spec_lock(plan: DeckPlan) -> str:
    lines = [
        "## canvas",
        "- viewBox: 0 0 1280 720",
        "- format: PPT 16:9",
        "",
        "## colors",
        "- bg: #FFFFFF",
        "- primary: #1F3FB7",
        "- accent: #63A3FF",
        "- secondary_accent: #DCE7FF",
        "- text: #1F2937",
        "- text_secondary: #6B7280",
        "- border: #D9E2F1",
        "",
        "## typography",
        '- font_family: "Microsoft YaHei", Arial, sans-serif',
        "- title_family: Arial, sans-serif",
        '- body_family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif',
        "- code_family: Consolas, \"Courier New\", monospace",
        "- body: 22",
        "- title: 36",
        "- subtitle: 24",
        "- annotation: 14",
        "",
        "## icons",
        "- library: chunk",
        "- inventory: sparkles, device-mobile, camera, battery, presentation",
        "",
        "## page_rhythm",
    ]
    for page in plan.pages:
        lines.append(f"- P{page.index:02d}: {page.page_rhythm}")
    lines.extend(
        [
            "",
            "## forbidden",
            "- Mixing icon libraries",
            "- rgba()",
            "- <style>, class, <foreignObject>, textPath, @font-face, <animate*>, <script>, <iframe>, <symbol>+<use>",
            "- <g opacity> (set opacity on each child element individually)",
        ]
    )
    return "\n".join(lines) + "\n"
