from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.modules.ppt.repository import PptRepository
from app.modules.ppt.schemas import (
    PptComponentItemSchema,
    PptDeckCreateRequest,
    PptDeckHistorySchema,
    PptDeckModifyRequest,
    PptDeckSchema,
    PptExportSchema,
    PptMetricSchema,
    PptSlideSchema,
    PptThemeSchema,
    SlideLayout,
    ThemeId,
    coerce_text_list,
    normalize_theme_id,
    sanitize_display_text,
)
from app.services.llm_client import LlmClient
from app.services.pptx_export_service import PptxExportService

THEMES: dict[ThemeId, dict[str, str]] = {
    "business": {
        "label": "business 商务风",
        "background": "#002F6C",
        "title": "#FFFFFF",
        "body": "#F2F2F2",
        "component": "#4F81BD",
        "secondary": "#FFFFFF",
        "line": "#4F81BD",
        "card": "#4F81BD",
        "muted": "#D9E6F2",
    },
    "academic": {
        "label": "academic 学术风",
        "background": "#F8F8F8",
        "title": "#1A2E42",
        "body": "#333333",
        "component": "#4A90E2",
        "secondary": "#FFFFFF",
        "line": "#D6E7F8",
        "card": "#FFFFFF",
        "muted": "#5B6B7A",
    },
    "apple_black": {
        "label": "apple_black 苹果黑风",
        "background": "#1C1C1C",
        "title": "#FFFFFF",
        "body": "#E5E5E5",
        "component": "#FFD700",
        "secondary": "#2A2A2A",
        "line": "#5A5A5A",
        "card": "#2A2A2A",
        "muted": "#A9A9A9",
    },
    "apple_white": {
        "label": "apple_white 苹果白风",
        "background": "#FFFFFF",
        "title": "#000000",
        "body": "#222222",
        "component": "#4A90E2",
        "secondary": "#F0F4FA",
        "line": "#D9E2F0",
        "card": "#FFFFFF",
        "muted": "#5A6470",
    },
    "eco": {
        "label": "eco 绿色环保风",
        "background": "#DAD7CD",
        "title": "#333333",
        "body": "#333333",
        "component": "#588157",
        "secondary": "#A3B18A",
        "line": "#3A5A40",
        "card": "#A3B18A",
        "muted": "#4C5F46",
    },
}

VALID_LAYOUTS: set[str] = {
    "cover",
    "bullets",
    "two_column",
    "timeline",
    "metrics",
    "summary",
    "section_divider",
    "quote",
    "comparison",
    "process",
    "matrix",
    "architecture",
}


class PptService:
    def __init__(
        self,
        repository: PptRepository,
        *,
        llm_client: LlmClient | None = None,
        export_service: PptxExportService | None = None,
        generated_root: Path | None = None,
    ) -> None:
        self._repository = repository
        self._llm_client = llm_client or LlmClient()
        self._export_service = export_service or PptxExportService()
        self._generated_root = generated_root or Path(get_settings().GENERATED_ROOT)

    def list_themes(self) -> list[PptThemeSchema]:
        return [
            PptThemeSchema(theme_id=theme_id, label=theme["label"])
            for theme_id, theme in THEMES.items()
        ]

    def create_deck(self, payload: PptDeckCreateRequest) -> PptDeckSchema:
        deck = self._build_deck(self._apply_slide_limit_from_content(payload))
        self._persist_deck_artifacts(deck)
        return self._repository.save(deck)

    def modify_deck(self, deck_id: str, payload: PptDeckModifyRequest) -> PptDeckSchema:
        deck = self._resolve_deck(deck_id, payload.current_deck)
        updated = self._modify_deck_with_deepseek(deck, payload)
        updated = self._sanitize_deck(updated)

        modified_at = self._timestamp()
        updated = updated.model_copy(
            update={
                "html": self._render_html(updated),
                "last_modified": modified_at,
                "history": [
                    *updated.history,
                    PptDeckHistorySchema(
                        action="modify",
                        version=updated.version,
                        timestamp=modified_at,
                        summary="Applied natural language deck modification",
                        instruction=payload.instruction,
                    ),
                ],
            }
        )
        self._persist_deck_artifacts(updated)
        return self._repository.save(updated)

    def _resolve_deck(
        self,
        deck_id: str,
        current_deck: PptDeckSchema | dict[str, object] | None,
    ) -> PptDeckSchema:
        try:
            return self._repository.get(deck_id)
        except KeyError:
            if current_deck is None:
                raise
            deck = (
                current_deck
                if isinstance(current_deck, PptDeckSchema)
                else PptDeckSchema.model_validate(current_deck)
            )
            if deck.deck_id != deck_id:
                raise KeyError(f"deck {deck_id} not found")
            return deck

    def export_deck(self, deck_id: str) -> PptExportSchema:
        deck = self._sanitize_deck(self._repository.get(deck_id))
        artifact_dir = self._deck_dir(deck.deck_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        self._persist_deck_artifacts(deck)

        export_result = self._export_service.export(
            deck=deck.model_dump(mode="json"),
            html_path=artifact_dir / "index.html",
            output_dir=artifact_dir / "exports",
        )
        exported = self._repository.save(
            deck.model_copy(
                update={
                    "history": [
                        *deck.history,
                        PptDeckHistorySchema(
                            action="export",
                            version=deck.version,
                            timestamp=self._timestamp(),
                            summary="Exported PPTX artifact",
                        ),
                    ]
                }
            )
        )
        return PptExportSchema(
            deck_id=exported.deck_id,
            file_name=Path(export_result["path"]).name,
            path=export_result["path"],
            url=export_result["url"],
            version=exported.version,
        )

    def _build_deck(self, payload: PptDeckCreateRequest) -> PptDeckSchema:
        deck_id = f"deck_{uuid4().hex[:12]}"
        normalized = self._generate_content(payload)
        timestamp = self._timestamp()
        deck = PptDeckSchema(
            deck_id=deck_id,
            type=payload.type,
            title=normalized["title"],
            source_content=payload.content,
            theme=normalized["theme"],
            author=payload.preferences.author,
            version=1,
            last_modified=timestamp,
            slides=normalized["slides"],
            html="",
            history=[
                PptDeckHistorySchema(
                    action="create",
                    version=1,
                    timestamp=timestamp,
                    summary="Created deck from structured content generation",
                )
            ],
        )
        deck = self._sanitize_deck(deck)
        return deck.model_copy(update={"html": self._render_html(deck)})

    def _apply_slide_limit_from_content(
        self,
        payload: PptDeckCreateRequest,
    ) -> PptDeckCreateRequest:
        parsed_slide_limit = self._extract_slide_limit(payload.content)
        if parsed_slide_limit is None:
            return payload
        return payload.model_copy(
            update={
                "preferences": payload.preferences.model_copy(
                    update={"slides_limit": parsed_slide_limit}
                )
            }
        )

    def _generate_content(self, payload: PptDeckCreateRequest) -> dict[str, object]:
        if not self._llm_client.is_configured():
            raise RuntimeError("DeepSeek API is not configured for PPT generation")

        response = self._llm_client.complete_json(
            system_prompt=(
                "You are DeepSeek v4flash generating structured JSON for presentation decks. "
                "Return JSON only with title, theme, slides[].layout, slides[].title, "
                "and the layout-specific fields. Available layouts: "
                "cover(title, subtitle, kicker), bullets(title, body, notes), "
                "two_column(title, left_title, right_title, left, right, notes), "
                "timeline(title, items, notes), metrics(title, metrics[{label, value, note}], notes), "
                "summary(title, body, actions, notes), "
                "section_divider(title, kicker, subtitle, notes), "
                "quote(title, quote, source, notes), "
                "comparison(title, left_title, right_title, left, right, notes), "
                "process(title, items, notes), "
                "matrix(title, quadrants[{title, body}], notes), "
                "architecture(title, blocks[{title, body}] or items, notes). "
                "Choose layouts based on the content and vary them across the deck when appropriate. "
                "Prefer structural layouts when the source content suggests sections, comparisons, steps, "
                "architecture, or key takeaways. Do not make every slide bullets unless the content truly requires it. "
                "Optional slides[].images may still be returned for any layout. "
                "Do not return markdown fences."
            ),
            user_prompt=json.dumps(
                {
                    "type": payload.type,
                    "content": payload.content,
                    "preferences": payload.preferences.model_dump(mode="json"),
                },
                ensure_ascii=False,
            ),
            timeout=120,
            max_tokens=4000,
        )

        return self._normalize_llm_deck(response, payload)

    def _fallback_generate(self, payload: PptDeckCreateRequest) -> dict[str, object]:
        segments = self._split_content(payload.content)
        slide_count = payload.preferences.slides_limit
        title = self._derive_title(payload.content)
        slides: list[PptSlideSchema] = []

        for index in range(slide_count):
            seed = segments[index % len(segments)]
            details = self._derive_bullets(seed, payload.content)
            slide_id = f"slide_{uuid4().hex[:10]}"
            slides.append(
                PptSlideSchema(
                    id=slide_id,
                    slide_id=slide_id,
                    title=self._slide_title(index, seed),
                    body=details,
                    images=[],
                    notes=f"Source type: {payload.type}",
                    theme=payload.preferences.theme,
                    author=payload.preferences.author,
                    last_modified=self._timestamp(),
                    version=1,
                )
            )

        return {
            "title": title,
            "theme": payload.preferences.theme,
            "slides": slides,
        }

    def _normalize_llm_deck(
        self,
        response: dict[str, object],
        payload: PptDeckCreateRequest,
    ) -> dict[str, object]:
        theme = self._normalize_theme(str(response.get("theme") or payload.preferences.theme))
        raw_slides = response.get("slides")
        if not isinstance(raw_slides, list) or not raw_slides:
            raise RuntimeError("DeepSeek response did not include slides")

        slides: list[PptSlideSchema] = []
        for raw_slide in raw_slides[: payload.preferences.slides_limit]:
            if not isinstance(raw_slide, dict):
                continue
            slides.append(
                self._normalize_slide_payload(
                    raw_slide,
                    theme=theme,
                    author=payload.preferences.author,
                    version=1,
                )
            )

        if not slides:
            raise RuntimeError("DeepSeek response did not include usable slides")

        return {
            "title": str(response.get("title") or self._derive_title(payload.content)),
            "theme": theme,
            "slides": slides,
        }

    def _modify_deck_with_deepseek(
        self,
        deck: PptDeckSchema,
        payload: PptDeckModifyRequest,
    ) -> PptDeckSchema:
        if not self._llm_client.is_configured():
            raise RuntimeError("DeepSeek API is not configured for PPT modification")

        response = self._llm_client.complete_json(
            system_prompt=(
                "You are DeepSeek v4flash updating presentation deck JSON. "
                "Return JSON only with optional theme and slides[]. "
                "Only include slides that changed, preserving their slide_id/id."
            ),
            user_prompt=json.dumps(
                {
                    "instruction": payload.instruction,
                    "slide_id": payload.slide_id,
                    "deck": deck.model_dump(mode="json"),
                },
                ensure_ascii=False,
            ),
            timeout=120,
            max_tokens=4000,
        )

        raw_slides = response.get("slides")
        if not isinstance(raw_slides, list):
            raise RuntimeError("DeepSeek response did not include slides")

        slide_lookup = {slide.slide_id: slide for slide in deck.slides}
        updated_slides: list[PptSlideSchema] = []
        modified_at = self._timestamp()
        next_theme = self._normalize_theme(str(response.get("theme") or deck.theme))
        for raw_slide in raw_slides:
            if not isinstance(raw_slide, dict):
                continue
            slide_id = str(raw_slide.get("slide_id") or raw_slide.get("id") or "")
            original = slide_lookup.get(slide_id)
            if original is None:
                continue
            updated_slides.append(
                self._normalize_slide_payload(
                    raw_slide,
                    theme=next_theme,
                    author=deck.author,
                    version=original.version + 1,
                    slide_id=original.slide_id,
                    existing=original,
                    last_modified=modified_at,
                )
            )

        if not updated_slides:
            raise RuntimeError("DeepSeek response did not include usable slide updates")

        by_id = {slide.slide_id: slide for slide in updated_slides}
        return deck.model_copy(
            update={
                "theme": next_theme,
                "slides": [
                    by_id.get(
                        slide.slide_id,
                        slide.model_copy(update={"theme": next_theme})
                        if next_theme != slide.theme
                        else slide,
                    )
                    for slide in deck.slides
                ],
                "version": deck.version + 1,
            }
        )

    def _persist_deck_artifacts(self, deck: PptDeckSchema) -> None:
        artifact_dir = self._deck_dir(deck.deck_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "index.html").write_text(deck.html, encoding="utf-8")
        (artifact_dir / "deck.json").write_text(
            json.dumps(deck.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _sanitize_deck(self, deck: PptDeckSchema) -> PptDeckSchema:
        sanitized_slides = [
            slide.model_copy(
                update={
                    "title": self._sanitize_markdown_text(slide.title) or "内容页",
                    "body": self._sanitize_body_items(slide.body) or ["待补充要点"],
                    "subtitle": self._sanitize_markdown_text(slide.subtitle) or None,
                    "kicker": self._sanitize_markdown_text(slide.kicker) or None,
                    "quote": self._sanitize_markdown_text(slide.quote) or None,
                    "source": self._sanitize_markdown_text(slide.source) or None,
                    "left_title": self._sanitize_markdown_text(slide.left_title) or None,
                    "right_title": self._sanitize_markdown_text(slide.right_title) or None,
                    "left": self._sanitize_body_items(slide.left),
                    "right": self._sanitize_body_items(slide.right),
                    "items": self._sanitize_body_items(slide.items),
                    "quadrants": [
                        item.model_copy(
                            update={
                                "title": self._sanitize_markdown_text(item.title) or "模块",
                                "body": self._sanitize_markdown_text(item.body) or None,
                                "subtitle": self._sanitize_markdown_text(item.subtitle) or None,
                                "source": self._sanitize_markdown_text(item.source) or None,
                            }
                        )
                        for item in slide.quadrants
                    ],
                    "blocks": [
                        item.model_copy(
                            update={
                                "title": self._sanitize_markdown_text(item.title) or "模块",
                                "body": self._sanitize_markdown_text(item.body) or None,
                                "subtitle": self._sanitize_markdown_text(item.subtitle) or None,
                                "source": self._sanitize_markdown_text(item.source) or None,
                            }
                        )
                        for item in slide.blocks
                    ],
                    "metrics": [
                        metric.model_copy(
                            update={
                                "label": self._sanitize_markdown_text(metric.label) or "指标",
                                "value": self._sanitize_markdown_text(metric.value) or "-",
                                "note": self._sanitize_markdown_text(metric.note) or None,
                            }
                        )
                        for metric in slide.metrics
                    ],
                    "actions": self._sanitize_body_items(slide.actions),
                    "notes": (
                        self._sanitize_markdown_text(slide.notes)
                        if slide.notes
                        else None
                    ),
                }
            )
            for slide in deck.slides
        ]
        return deck.model_copy(
            update={
                "title": self._sanitize_markdown_text(deck.title) or "未命名演示文稿",
                "slides": sanitized_slides,
            }
        )

    def _sanitize_body_items(self, items: list[str]) -> list[str]:
        return [cleaned for item in items if (cleaned := self._sanitize_markdown_text(item))]

    def _sanitize_markdown_text(self, text: object | None) -> str:
        return sanitize_display_text(text)

    def _deck_dir(self, deck_id: str) -> Path:
        return self._generated_root / "ppt" / deck_id

    def _normalize_slide_payload(
        self,
        raw_slide: dict[str, object],
        *,
        theme: ThemeId,
        author: str | None,
        version: int,
        slide_id: str | None = None,
        existing: PptSlideSchema | None = None,
        last_modified: str | None = None,
    ) -> PptSlideSchema:
        if "layout" in raw_slide:
            resolved_layout = self._normalize_layout(raw_slide.get("layout"))
        else:
            resolved_layout = existing.layout if existing else "bullets"
        resolved_slide_id = slide_id or existing.slide_id if existing else slide_id
        if not resolved_slide_id:
            resolved_slide_id = f"slide_{uuid4().hex[:10]}"

        body = self._coerce_string_list(raw_slide.get("body"), existing.body if existing else [])
        left = self._coerce_string_list(raw_slide.get("left"), existing.left if existing else [])
        right = self._coerce_string_list(raw_slide.get("right"), existing.right if existing else [])
        items = self._coerce_string_list(raw_slide.get("items"), existing.items if existing else [])
        quadrants = self._coerce_component_items(
            raw_slide.get("quadrants"),
            existing.quadrants if existing else [],
        )
        blocks = self._coerce_component_items(
            raw_slide.get("blocks") or raw_slide.get("items"),
            existing.blocks if existing else [],
        )
        actions = self._coerce_string_list(raw_slide.get("actions"), existing.actions if existing else [])
        metrics = self._coerce_metrics(raw_slide.get("metrics"), existing.metrics if existing else [])
        raw_images = raw_slide.get("images")

        if resolved_layout == "bullets" and not body:
            body = existing.body if existing and existing.body else ["待补充要点"]
        if resolved_layout == "summary" and not body:
            body = existing.body if existing and existing.body else ["总结要点待补充"]
        if resolved_layout in {"two_column", "comparison"}:
            left = left or (existing.left if existing else []) or ["待补充"]
            right = right or (existing.right if existing else []) or ["待补充"]
        if resolved_layout in {"timeline", "process"} and not items:
            items = existing.items if existing and existing.items else ["待补充时间节点"]
        if resolved_layout == "metrics" and not metrics:
            metrics = existing.metrics if existing and existing.metrics else [
                PptMetricSchema(label="关键指标", value="待补充")
            ]
        if resolved_layout == "summary" and not actions:
            actions = existing.actions if existing and existing.actions else ["补充后续动作"]
        if resolved_layout == "quote":
            items = []
        if resolved_layout == "matrix" and not quadrants:
            quadrants = (
                existing.quadrants if existing and existing.quadrants else [
                    PptComponentItemSchema(title="高价值高紧急", body="待补充"),
                    PptComponentItemSchema(title="高价值低紧急", body="待补充"),
                    PptComponentItemSchema(title="低价值高紧急", body="待补充"),
                    PptComponentItemSchema(title="低价值低紧急", body="待补充"),
                ]
            )
        if resolved_layout == "architecture" and not blocks:
            blocks = existing.blocks if existing and existing.blocks else [
                PptComponentItemSchema(title="模块一", body="待补充"),
                PptComponentItemSchema(title="模块二", body="待补充"),
                PptComponentItemSchema(title="模块三", body="待补充"),
            ]

        return PptSlideSchema(
            id=resolved_slide_id,
            slide_id=resolved_slide_id,
            layout=resolved_layout,
            title=str(raw_slide.get("title") or (existing.title if existing else "内容页")),
            body=body,
            subtitle=self._coerce_optional_string(raw_slide.get("subtitle"), existing.subtitle if existing else None),
            kicker=self._coerce_optional_string(raw_slide.get("kicker"), existing.kicker if existing else None),
            quote=self._coerce_optional_string(raw_slide.get("quote"), existing.quote if existing else None),
            source=self._coerce_optional_string(raw_slide.get("source"), existing.source if existing else None),
            left_title=self._coerce_optional_string(raw_slide.get("left_title"), existing.left_title if existing else None),
            right_title=self._coerce_optional_string(raw_slide.get("right_title"), existing.right_title if existing else None),
            left=left,
            right=right,
            items=items,
            quadrants=quadrants,
            blocks=blocks,
            metrics=metrics,
            actions=actions,
            images=[str(item) for item in raw_images] if isinstance(raw_images, list) else (existing.images if existing else []),
            notes=self._coerce_optional_string(raw_slide.get("notes"), existing.notes if existing else None),
            theme=theme,
            author=author,
            last_modified=last_modified or self._timestamp(),
            version=version,
        )

    def _normalize_layout(self, value: object, default: SlideLayout = "bullets") -> SlideLayout:
        layout = str(value or "").strip().lower()
        return layout if layout in VALID_LAYOUTS else default

    def _coerce_optional_string(self, value: object, default: str | None = None) -> str | None:
        if value is None:
            return default
        text = sanitize_display_text(value)
        return text or default

    def _coerce_string_list(self, value: object, default: list[str] | None = None) -> list[str]:
        coerced = coerce_text_list(value)
        return coerced or list(default or [])

    def _coerce_metrics(
        self,
        value: object,
        default: list[PptMetricSchema] | None = None,
    ) -> list[PptMetricSchema]:
        if not isinstance(value, list):
            return list(default or [])

        metrics: list[PptMetricSchema] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            metric_value = str(item.get("value") or "").strip()
            if not label and not metric_value:
                continue
            metrics.append(
                PptMetricSchema(
                    label=label or "指标",
                    value=metric_value or "-",
                    note=self._coerce_optional_string(item.get("note")),
                )
            )
        return metrics

    def _coerce_component_items(
        self,
        value: object,
        default: list[PptComponentItemSchema] | None = None,
    ) -> list[PptComponentItemSchema]:
        if not isinstance(value, list):
            return list(default or [])

        items: list[PptComponentItemSchema] = []
        for item in value:
            if isinstance(item, dict):
                title = self._coerce_optional_string(item.get("title")) or self._coerce_optional_string(item.get("label"))
                body = self._coerce_optional_string(item.get("body")) or self._coerce_optional_string(item.get("description"))
                subtitle = self._coerce_optional_string(item.get("subtitle"))
                source = self._coerce_optional_string(item.get("source"))
                if not title and not body:
                    continue
                items.append(
                    PptComponentItemSchema(
                        title=title or "模块",
                        body=body,
                        subtitle=subtitle,
                        source=source,
                    )
                )
                continue
            cleaned = self._sanitize_markdown_text(item)
            if cleaned:
                items.append(PptComponentItemSchema(title=cleaned))
        return items

    def _render_html(self, deck: PptDeckSchema) -> str:
        theme = THEMES.get(deck.theme, THEMES["apple_white"])
        sections = []
        for slide in deck.slides:
            sections.append(self._render_slide_html(slide, deck.theme))

        return (
            "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<title>{escape(deck.title)}</title>"
            "<style>"
            f":root{{--bg:{theme['background']};--title:{theme['title']};--body:{theme['body']};--component:{theme['component']};--secondary:{theme.get('secondary', theme['card'])};--line:{theme['line']};--card:{theme['card']};--muted:{theme['muted']};}}"
            "body{margin:0;padding:32px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
            "background:var(--bg);color:var(--body);display:grid;gap:24px;}"
            ".deck-header{display:flex;justify-content:space-between;align-items:end;gap:16px;}"
            ".deck-header h1{margin:0;font-size:32px;color:var(--title);}.deck-header p{margin:4px 0 0;color:var(--muted);}"
            ".slide{min-height:540px;padding:40px;border:1px solid var(--line);"
            "background:transparent;box-sizing:border-box;overflow:hidden;}"
            ".slide h2{margin:0 0 18px;font-size:28px;color:var(--title);}.slide ul{margin:0;padding-left:24px;display:grid;gap:10px;font-size:18px;}"
            ".slide-meta{font-size:12px;color:var(--muted);margin-bottom:18px;text-transform:uppercase;}"
            ".notes{margin-top:24px;color:var(--muted);font-size:14px;}"
            ".slide-shell{display:grid;gap:20px;height:100%;}.eyebrow{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--component);}"
            ".surface{background:var(--card);border:1px solid var(--line);box-sizing:border-box;}"
            ".hero{display:grid;align-content:center;justify-items:center;text-align:center;min-height:420px;gap:18px;}"
            ".hero h2{font-size:42px;margin:0;color:var(--title);}.hero p{margin:0;font-size:20px;color:var(--body);}"
            ".section-divider{display:grid;align-content:center;min-height:400px;padding:36px;border-left:8px solid var(--component);background:linear-gradient(135deg,var(--secondary),transparent 70%);}"
            ".section-divider h2{font-size:52px;line-height:1.05;}.section-divider p{margin:0;font-size:19px;color:var(--muted);max-width:75%;}"
            ".quote-panel{display:grid;gap:18px;padding:32px;min-height:360px;grid-template-columns:auto 1fr;align-items:start;}.quote-mark{font-size:84px;line-height:.8;color:var(--component);font-weight:700;}"
            ".quote-copy{display:grid;gap:14px;}.quote-copy blockquote{margin:0;font-size:30px;line-height:1.35;color:var(--title);}.quote-source{font-size:16px;color:var(--muted);}"
            ".two-column-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;}.column-panel{padding:22px;border:1px solid var(--line);background:var(--card);}"
            ".comparison-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;}.comparison-panel{padding:24px;border-top:6px solid var(--component);display:grid;gap:16px;}.comparison-panel h3{margin:0;font-size:18px;color:var(--title);}"
            ".column-panel h3,.metric-card h3{margin:0 0 14px;font-size:18px;color:var(--title);}.column-panel ul{font-size:17px;}"
            ".timeline-track{display:grid;gap:18px;position:relative;padding-left:18px;}.timeline-track:before{content:'';position:absolute;left:4px;top:6px;bottom:6px;width:2px;background:var(--line);}"
            ".timeline-item{position:relative;padding-left:18px;font-size:19px;color:var(--body);}.timeline-item:before{content:'';position:absolute;left:-1px;top:8px;width:10px;height:10px;border-radius:999px;background:var(--component);border:1px solid var(--line);}"
            ".process-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;align-items:stretch;}.process-step{position:relative;padding:20px 18px 20px 60px;}.process-index{position:absolute;left:18px;top:18px;width:28px;height:28px;border-radius:999px;background:var(--component);color:var(--secondary);display:grid;place-items:center;font-size:14px;font-weight:700;}.process-step p{margin:0;font-size:16px;color:var(--body);}"
            ".metrics-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;}.metric-card{padding:22px;border:1px solid var(--line);display:grid;gap:8px;background:var(--card);}"
            ".metric-value{font-size:32px;font-weight:700;color:var(--component);}.metric-note{color:var(--muted);font-size:14px;}"
            ".matrix-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;}.matrix-card{padding:22px;display:grid;gap:10px;min-height:150px;}.matrix-card h3,.architecture-block h3{margin:0;font-size:18px;color:var(--title);}.matrix-card p,.architecture-block p{margin:0;font-size:16px;color:var(--body);line-height:1.45;}"
            ".architecture-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;}.architecture-block{padding:22px;display:grid;gap:10px;position:relative;}.architecture-block:after{content:'';position:absolute;right:-11px;top:50%;width:22px;height:2px;background:var(--line);}.architecture-block:last-child:after{display:none;}"
            ".summary-grid{display:grid;grid-template-columns:1.4fr 1fr;gap:24px;}.summary-panel,.actions-panel{padding:22px;border:1px solid var(--line);background:var(--card);}"
            ".summary-panel ul,.actions-panel ul{font-size:17px;}"
            "@media (max-width:960px){.two-column-grid,.comparison-grid,.summary-grid,.process-grid,.matrix-grid,.architecture-grid{grid-template-columns:1fr;}.section-divider p{max-width:none;}.quote-panel{grid-template-columns:1fr;}.architecture-block:after{display:none;}}"
            "</style></head><body>"
            f"<header class='deck-header'><div><h1>{escape(deck.title)}</h1><p>author: {escape(deck.author or 'system')}</p></div>"
            f"<div><p>version {deck.version}</p><p>last modified {escape(deck.last_modified)}</p></div></header>"
            f"{''.join(sections)}</body></html>"
        )

    def _render_slide_html(self, slide: PptSlideSchema, theme: ThemeId) -> str:
        notes = f"<p class='notes'>{escape(slide.notes)}</p>" if slide.notes else ""
        base_open = (
            f"<section class='slide theme-{theme} layout-{escape(slide.layout.replace('_', '-'))}' "
            f"data-slide-id='{escape(slide.slide_id)}'>"
            f"<div class='slide-meta'>v{slide.version}</div>"
            "<div class='slide-shell'>"
        )
        if slide.layout == "cover":
            kicker = f"<div class='eyebrow'>{escape(slide.kicker)}</div>" if slide.kicker else ""
            subtitle = f"<p>{escape(slide.subtitle)}</p>" if slide.subtitle else ""
            return f"{base_open}<div class='hero surface'>{kicker}<h2>{escape(slide.title)}</h2>{subtitle}</div>{notes}</div></section>"
        if slide.layout == "section_divider":
            kicker = f"<div class='eyebrow'>{escape(slide.kicker)}</div>" if slide.kicker else ""
            subtitle = f"<p>{escape(slide.subtitle)}</p>" if slide.subtitle else ""
            return f"{base_open}<div class='section-divider surface'>{kicker}<h2>{escape(slide.title)}</h2>{subtitle}</div>{notes}</div></section>"
        if slide.layout == "quote":
            quote = escape(slide.quote or "待补充结论")
            source = f"<div class='quote-source'>{escape(slide.source)}</div>" if slide.source else ""
            return (
                f"{base_open}<div class='quote-panel surface'>"
                "<div class='quote-mark'>“</div>"
                f"<div class='quote-copy'><h2>{escape(slide.title)}</h2><blockquote>{quote}</blockquote>{source}</div>"
                f"</div>{notes}</div></section>"
            )
        if slide.layout == "two_column":
            left_items = "".join(f"<li>{escape(item)}</li>" for item in slide.left)
            right_items = "".join(f"<li>{escape(item)}</li>" for item in slide.right)
            return (
                f"{base_open}<h2>{escape(slide.title)}</h2>"
                "<div class='two-column-grid'>"
                f"<article class='column-panel'><h3>{escape(slide.left_title or '左侧')}</h3><ul>{left_items}</ul></article>"
                f"<article class='column-panel'><h3>{escape(slide.right_title or '右侧')}</h3><ul>{right_items}</ul></article>"
                f"</div>{notes}</div></section>"
            )
        if slide.layout == "comparison":
            left_items = "".join(f"<li>{escape(item)}</li>" for item in slide.left)
            right_items = "".join(f"<li>{escape(item)}</li>" for item in slide.right)
            return (
                f"{base_open}<h2>{escape(slide.title)}</h2>"
                "<div class='comparison-grid'>"
                f"<article class='comparison-panel surface'><h3>{escape(slide.left_title or '方案 A')}</h3><ul>{left_items}</ul></article>"
                f"<article class='comparison-panel surface'><h3>{escape(slide.right_title or '方案 B')}</h3><ul>{right_items}</ul></article>"
                f"</div>{notes}</div></section>"
            )
        if slide.layout == "timeline":
            items = "".join(f"<div class='timeline-item'>{escape(item)}</div>" for item in slide.items)
            return f"{base_open}<h2>{escape(slide.title)}</h2><div class='timeline-track'>{items}</div>{notes}</div></section>"
        if slide.layout == "process":
            steps = "".join(
                f"<article class='process-step surface'><div class='process-index'>{index}</div><p>{escape(item)}</p></article>"
                for index, item in enumerate(slide.items[:6], start=1)
            )
            return f"{base_open}<h2>{escape(slide.title)}</h2><div class='process-grid'>{steps}</div>{notes}</div></section>"
        if slide.layout == "metrics":
            cards = "".join(
                (
                    "<article class='metric-card'>"
                    + f"<h3>{escape(metric.label)}</h3>"
                    + f"<div class='metric-value'>{escape(metric.value)}</div>"
                    + (
                        f"<div class='metric-note'>{escape(metric.note)}</div>"
                        if metric.note
                        else ""
                    )
                    + "</article>"
                )
                for metric in slide.metrics
            )
            return f"{base_open}<h2>{escape(slide.title)}</h2><div class='metrics-grid'>{cards}</div>{notes}</div></section>"
        if slide.layout == "summary":
            body = "".join(f"<li>{escape(item)}</li>" for item in slide.body)
            actions = "".join(f"<li>{escape(item)}</li>" for item in slide.actions)
            return (
                f"{base_open}<h2>{escape(slide.title)}</h2>"
                "<div class='summary-grid'>"
                f"<article class='summary-panel'><h3>总结</h3><ul>{body}</ul></article>"
                f"<article class='actions-panel'><h3>行动项</h3><ul>{actions}</ul></article>"
                f"</div>{notes}</div></section>"
            )
        if slide.layout == "matrix":
            cards = "".join(
                f"<article class='matrix-card surface'><h3>{escape(item.title)}</h3><p>{escape(item.body or '')}</p></article>"
                for item in slide.quadrants[:4]
            )
            return f"{base_open}<h2>{escape(slide.title)}</h2><div class='matrix-grid'>{cards}</div>{notes}</div></section>"
        if slide.layout == "architecture":
            blocks = "".join(
                f"<article class='architecture-block surface'><h3>{escape(item.title)}</h3><p>{escape(item.body or '')}</p></article>"
                for item in slide.blocks[:4]
            )
            return f"{base_open}<h2>{escape(slide.title)}</h2><div class='architecture-grid'>{blocks}</div>{notes}</div></section>"

        bullets = "".join(f"<li>{escape(item)}</li>" for item in slide.body)
        return f"{base_open}<h2>{escape(slide.title)}</h2><ul>{bullets}</ul>{notes}</div></section>"

    def _split_content(self, content: str) -> list[str]:
        pieces = [part.strip() for part in re.split(r"[。\n；;!?]+", content) if part.strip()]
        return pieces or [content.strip()]

    def _extract_slide_limit(self, content: str) -> int | None:
        text = content.strip()
        if not text:
            return None

        range_match = re.search(
            r"(\d{1,2})\s*[-~到至]\s*(\d{1,2})\s*页",
            text,
            flags=re.IGNORECASE,
        )
        if range_match:
            return self._clamp_slide_limit(int(range_match.group(2)))

        digit_match = re.search(r"(?<!第)(\d{1,2})\s*页", text, flags=re.IGNORECASE)
        if digit_match:
            return self._clamp_slide_limit(int(digit_match.group(1)))

        chinese_match = re.search(r"(?<!第)([零一二两三四五六七八九十]+)\s*页", text)
        if chinese_match:
            parsed = self._parse_chinese_slide_count(chinese_match.group(1))
            if parsed is not None:
                return self._clamp_slide_limit(parsed)

        return None

    def _parse_chinese_slide_count(self, value: str) -> int | None:
        numerals = {
            "零": 0,
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
        }
        if value == "十":
            return 10
        if value == "十一":
            return 11
        if value == "十二":
            return 12
        if value.startswith("十") and len(value) == 2:
            return 10 + numerals.get(value[1], 0)
        if value.endswith("十") and len(value) == 2:
            return numerals.get(value[0], 0) * 10
        return numerals.get(value)

    def _clamp_slide_limit(self, value: int) -> int:
        return max(1, min(20, value))

    def _derive_title(self, content: str) -> str:
        first_line = self._split_content(content)[0]
        return first_line[:28] if len(first_line) > 28 else first_line

    def _derive_bullets(self, segment: str, content: str) -> list[str]:
        base = segment[:48] if len(segment) > 48 else segment
        return [
            base,
            f"结合原始内容提炼执行要点：{content[:42]}",
            "预留二次修改与导出链路，便于继续迭代。",
        ]

    def _slide_title(self, index: int, segment: str) -> str:
        if index == 0:
            return "执行摘要"
        return f"第 {index + 1} 页 | {segment[:18]}"

    def _instruction_bullets(self, instruction: str) -> list[str]:
        cleaned = instruction.strip()
        if not cleaned:
            return ["已根据指令更新内容。"]
        return [
            cleaned,
            f"重点更新：{cleaned[:36]}",
        ]

    def _extract_theme_from_instruction(self, instruction: str) -> ThemeId | None:
        lowered = instruction.lower()
        if any(
            token in instruction or token in lowered
            for token in ("business", "商务", "商务风", "商业", "orange", "活泼", "活泼橙")
        ):
            return "business"
        if any(token in instruction or token in lowered for token in ("academic", "学术", "学术风", "sky", "天空", "天空蓝")):
            return "academic"
        if any(
            token in instruction or token in lowered
            for token in ("apple_black", "苹果黑风", "tech", "科技", "科技风", "jewel", "宝石", "宝石蓝")
        ):
            return "apple_black"
        if any(
            token in instruction or token in lowered
            for token in ("apple_white", "苹果白风", "apple", "minimal", "simple", "简约", "简约风")
        ):
            return "apple_white"
        if any(token in instruction or token in lowered for token in ("eco", "绿色环保风", "mint", "薄荷", "薄荷绿")):
            return "eco"
        return None

    def _extract_title_update(self, instruction: str) -> str | None:
        patterns = [
            r"标题(?:改为|改成|换成)[“\"']?([^”\"'。；;\n]+)[”\"']?",
            r"title\s*(?:to|=|:)\s*[“\"']?([^”\"'。；;\n]+)[”\"']?",
        ]
        for pattern in patterns:
            match = re.search(pattern, instruction, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _normalize_theme(self, theme: str) -> ThemeId:
        return normalize_theme_id(theme)

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()
