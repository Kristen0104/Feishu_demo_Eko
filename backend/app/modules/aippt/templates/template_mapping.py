from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateMapping:
    logical_name: str
    render_template: str


_LOGICAL_TO_RENDER: dict[str, str] = {
    "cover": "cover",
    "closing": "closing",
    "toc": "toc",
    "chapter": "chapter",
    "content": "metrics",
    "content_overview": "three_cards",
    "content_timeline": "timeline",
    "content_metrics": "metrics",
    "content_matrix": "matrix",
    "content_swimlane": "swimlane",
}

_ALIASES: dict[str, str] = {
    "title": "cover",
    "chapter": "chapter",
    "ending": "closing",
    "end": "closing",
    "next_steps": "closing",
    "agenda": "toc",
    "table_of_contents": "toc",
    "content_page": "content",
    "content_variant_overview": "content_overview",
    "content_variant_timeline": "content_timeline",
    "content_variant_metrics": "content_metrics",
    "content_variant_matrix": "content_matrix",
    "content_variant_swimlane": "content_swimlane",
}

_DEFAULT_SEQUENCE = ["cover", "toc", "content"]
_CONTENT_VARIANTS = ["content_overview", "content_timeline", "content_metrics", "content_matrix", "content_swimlane"]


def template_for_position(slide_number: int) -> str:
    if slide_number <= len(_DEFAULT_SEQUENCE):
        return _DEFAULT_SEQUENCE[slide_number - 1]
    variant = _CONTENT_VARIANTS[(slide_number - len(_DEFAULT_SEQUENCE) - 1) % len(_CONTENT_VARIANTS)]
    return variant


def resolve_template(template_name: str) -> TemplateMapping:
    normalized = template_name.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = _ALIASES.get(normalized, normalized)

    if normalized in _LOGICAL_TO_RENDER:
        return TemplateMapping(logical_name=normalized, render_template=_LOGICAL_TO_RENDER[normalized])

    if "timeline" in normalized or "flow" in normalized or "phase" in normalized:
        return TemplateMapping(logical_name="content_timeline", render_template="timeline")
    if "metric" in normalized or "dashboard" in normalized or "chart" in normalized:
        return TemplateMapping(logical_name="content_metrics", render_template="metrics")
    if "matrix" in normalized or "map" in normalized or "quadrant" in normalized:
        return TemplateMapping(logical_name="content_matrix", render_template="matrix")
    if "swimlane" in normalized or "lane" in normalized or "handoff" in normalized:
        return TemplateMapping(logical_name="content_swimlane", render_template="swimlane")
    if "toc" in normalized or "agenda" in normalized:
        return TemplateMapping(logical_name="toc", render_template="toc")
    if "chapter" in normalized or "section" in normalized:
        return TemplateMapping(logical_name="chapter", render_template="chapter")
    if "cover" in normalized or "title" in normalized:
        return TemplateMapping(logical_name="cover", render_template="cover")
    if "ending" in normalized or "closing" in normalized or "next_step" in normalized:
        return TemplateMapping(logical_name="closing", render_template="closing")
    return TemplateMapping(logical_name="content_overview", render_template="three_cards")
