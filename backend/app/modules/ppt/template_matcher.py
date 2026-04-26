"""Heuristics for mapping imported PPTX references to official template families."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import json
import re


FALLBACK_TEMPLATE = "mckinsey"


KEYWORD_RULES: list[tuple[str, str]] = [
    ("government_red", "党"),
    ("government_red", "党建"),
    ("government_red", "红"),
    ("government_blue", "政府"),
    ("government_blue", "政务"),
    ("government_blue", "治理"),
    ("government_blue", "smart city"),
    ("ai_ops", "ai ops"),
    ("ai_ops", "telecom"),
    ("ai_ops", "数字化"),
    ("anthropic", "anthropic"),
    ("anthropic", "llm"),
    ("anthropic", "ai"),
    ("google_style", "google"),
    ("mckinsey", "mckinsey"),
    ("mckinsey", "consulting"),
    ("mckinsey", "strategy"),
    ("mckinsey", "investment"),
    ("medical_university", "医疗"),
    ("medical_university", "medical"),
    ("medical_university", "hospital"),
    ("psychology_attachment", "心理"),
    ("psychology_attachment", "counseling"),
    ("pixel_retro", "pixel"),
    ("pixel_retro", "retro"),
    ("china_telecom_template", "电信"),
    ("china_telecom_template", "telecom"),
    ("中国电建_现代", "电建"),
    ("中国电建_现代", "engineering"),
    ("中汽研_现代", "catarc"),
    ("招商银行", "银行"),
    ("科技蓝商务", "科技"),
    ("smart_red", "教育"),
]


def load_layout_catalog(catalog_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(catalog_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def infer_template_name(manifest: dict[str, Any], catalog: dict[str, dict[str, Any]]) -> str:
    text = _build_manifest_text(manifest)
    scores: Counter[str] = Counter()

    for template_name, entry in catalog.items():
        haystack = " ".join(
            [template_name, entry.get("label", ""), entry.get("summary", ""), " ".join(entry.get("keywords", []))]
        ).lower()
        for token in _tokenize(text):
            if token and token in haystack:
                scores[template_name] += 2

    for template_name, keyword in KEYWORD_RULES:
        if keyword.lower() in text.lower():
            scores[template_name] += 5

    if not scores:
        return FALLBACK_TEMPLATE

    best, _ = scores.most_common(1)[0]
    return best


def _build_manifest_text(manifest: dict[str, Any]) -> str:
    parts: list[str] = []
    source = manifest.get("source", {})
    parts.append(str(source.get("name", "")))
    theme = manifest.get("theme", {})
    parts.extend(theme.get("colors", {}).keys())
    parts.extend(theme.get("fonts", {}).values())
    for slide in manifest.get("slides", []):
        parts.append(str(slide.get("pageType", "")))
        parts.extend(slide.get("textSamples", []))
    parts.extend(manifest.get("pageTypeCandidates", {}).keys())
    return " ".join(parts)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text.lower())
