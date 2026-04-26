"""Template pack loading and rendering."""

from __future__ import annotations

import html
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .templates import validate_svg


LAYOUT_FILE_MAP = {
    "cover": "01_cover.svg",
    "toc": "02_toc.svg",
    "chapter": "02_chapter.svg",
    "content": "03_content.svg",
    "ending": "04_ending.svg",
}


@dataclass(frozen=True)
class TemplatePack:
    template_dir: Path
    name: str

    @classmethod
    def from_dir(cls, template_dir: str | Path) -> "TemplatePack":
        path = Path(template_dir)
        if not path.exists():
            raise FileNotFoundError(f"Template directory not found: {path}")
        return cls(template_dir=path, name=path.name)

    def has_layout(self, layout: str) -> bool:
        return _resolve_layout_path(self.template_dir, layout) is not None

    def render(self, page: dict[str, Any]) -> str:
        return self.render_direct(page)

    def render_direct(self, page: dict[str, Any]) -> str:
        layout = str(page.get("layout") or "content")
        svg_path = _resolve_layout_path(self.template_dir, layout)
        if svg_path is None:
            raise KeyError(f"Unknown template layout: {layout}")

        values = _build_placeholder_values(page)
        svg = svg_path.read_text(encoding="utf-8")
        svg = _substitute(svg, values)
        svg = _post_process_layout(svg, self.name, layout, page)
        validate_svg(svg)
        return svg


def _build_placeholder_values(page: dict[str, Any]) -> dict[str, str]:
    content = page.get("content", page.get("points", []))
    toc_items = _normalize_list(page.get("toc_items", []))
    thanks_items = _normalize_list(page.get("thanks_items", []))
    values = {
        "TITLE": _escape(page.get("title", "")),
        "TITLE_LINE2": _escape(page.get("title_line2", page.get("title2", ""))),
        "SUBTITLE": _escape(page.get("subtitle", "")),
        "PROJECT_CODE": _escape(page.get("project_code", "")),
        "DATE": _escape(page.get("date", "")),
        "PAGE_NUM": _escape(page.get("page_num", "")),
        "PAGE_TITLE": _escape(page.get("title", "")),
        "CHAPTER_NUM": _escape(page.get("chapter_num", "")),
        "CHAPTER_TITLE": _escape(page.get("title", "")),
        "CHAPTER_TITLE_EN": _escape(page.get("chapter_title_en", "")),
        "THANK_YOU": _escape(page.get("thank_you", page.get("title", "Thank You"))),
        "ENDING_SUBTITLE": _escape(page.get("subtitle", "")),
        "CLOSING_MESSAGE": _escape(page.get("closing_message", "")),
        "CONTACT_INFO": _escape(page.get("footer", "")),
        "SOURCE": _escape(page.get("source", "")),
        "SPEAKER_NAME": _escape(page.get("speaker_name", "")),
        "SPEAKER_TITLE": _escape(page.get("speaker_title", "")),
        "STATS_AREA": _escape(page.get("stats_area", "")),
        "CONTENT_AREA": _render_content_area(content),
    }

    for index in range(1, 6):
        values[f"TOC_ITEM_{index}_TITLE"] = _escape(_get_indexed_value(toc_items, index - 1, page.get(f"toc_item_{index}_title", "")))
        values[f"TOC_ITEM_{index}_DESC"] = _escape(page.get(f"toc_item_{index}_desc", ""))

    for index in range(1, 4):
        values[f"THANKS_PERSON_{index}"] = _escape(_get_indexed_value(thanks_items, index - 1, page.get(f"thanks_person_{index}", "")))
        values[f"THANKS_REASON_{index}"] = _escape(page.get(f"thanks_reason_{index}", ""))

    for key, value in page.items():
        if key.isupper() and isinstance(value, (str, int, float)):
            values[key] = _escape(value)
    return values


def _render_content_area(content: Any) -> str:
    if isinstance(content, list):
        items = [str(item).strip() for item in content if str(item).strip()]
    elif isinstance(content, str):
        items = [line.strip() for line in content.splitlines() if line.strip()]
    else:
        items = []

    if not items:
        return ""

    lines = []
    for index, item in enumerate(items[:8]):
        dy = 0 if index == 0 else 34
        lines.append(f'<tspan x="640" dy="{dy}">{_escape(item)}</tspan>')
    return "".join(lines)


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


def _get_indexed_value(items: list[str], index: int, fallback: Any) -> str:
    if index < len(items):
        return items[index]
    return str(fallback or "")


def _substitute(svg: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        svg = svg.replace(f"{{{{{key}}}}}", value)
    return svg


def _post_process_layout(svg: str, template_name: str, layout: str, page: dict[str, Any]) -> str:
    if template_name == "google_style" and layout == "content":
        svg = re.sub(
            r"\s*<text x=\"640\" y=\"420\"[^>]*>\s*\(由 Executor 根据实际内容自由布局\)\s*</text>",
            "",
            svg,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return svg


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _resolve_layout_path(template_dir: Path, layout: str) -> Path | None:
    filename = LAYOUT_FILE_MAP.get(layout)
    if not filename:
        return None
    root_candidate = template_dir / filename
    if root_candidate.exists():
        return root_candidate
    svg_candidate = template_dir / "svg" / filename
    if svg_candidate.exists():
        return svg_candidate
    return None
