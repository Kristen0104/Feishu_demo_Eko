from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ThemeId = Literal["business", "academic", "apple_black", "apple_white", "eco"]
DeckSourceType = Literal["text", "chat", "chat_record"]
SlideLayout = Literal[
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
]

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_STRONG_RE = re.compile(r"(\*\*|__)(.+?)\1")
MARKDOWN_EMPHASIS_RE = re.compile(
    r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)|(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)"
)
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
LEADING_LIST_MARKER_RE = re.compile(
    r"^\s*(?:(?:[-+*•·])|(?:\d+[.)])|(?:[A-Za-z][.)]))\s+"
)
MULTISPACE_RE = re.compile(r"\s+")


def normalize_theme_id(value: object) -> ThemeId:
    text = str(value or "").strip().lower()
    theme_map: dict[str, ThemeId] = {
        "business": "business",
        "商务": "business",
        "商务风": "business",
        "商业": "business",
        "academic": "academic",
        "学术": "academic",
        "学术风": "academic",
        "苹果黑风": "apple_black",
        "apple_black": "apple_black",
        "tech": "apple_black",
        "jewel": "apple_black",
        "宝石": "apple_black",
        "宝石蓝": "apple_black",
        "科技": "apple_black",
        "科技风": "apple_black",
        "apple_white": "apple_white",
        "apple": "apple_white",
        "苹果白风": "apple_white",
        "minimal": "apple_white",
        "simple": "apple_white",
        "简约": "apple_white",
        "简约风": "apple_white",
        "eco": "eco",
        "绿色环保风": "eco",
        "mint": "eco",
        "薄荷": "eco",
        "薄荷绿": "eco",
        "sky": "academic",
        "天空": "academic",
        "天空蓝": "academic",
        "orange": "business",
        "活泼": "business",
        "活泼橙": "business",
    }
    return theme_map.get(text, "apple_white")


def timestamp_now() -> str:
    return datetime.now(UTC).isoformat()


def sanitize_display_text(value: object | None) -> str:
    if value is None:
        return ""

    if isinstance(value, dict):
        return format_component_item(value)

    cleaned = str(value).strip()
    if not cleaned:
        return ""

    previous = None
    while cleaned != previous:
        previous = cleaned
        cleaned = MARKDOWN_LINK_RE.sub(r"\1", cleaned)
        cleaned = MARKDOWN_STRONG_RE.sub(r"\2", cleaned)
        cleaned = MARKDOWN_EMPHASIS_RE.sub(
            lambda match: match.group(1) or match.group(2) or "",
            cleaned,
        )
        cleaned = INLINE_CODE_RE.sub(r"\1", cleaned)

    cleaned = LEADING_LIST_MARKER_RE.sub("", cleaned)
    cleaned = MULTISPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def format_component_item(value: object | None) -> str:
    if value is None:
        return ""
    if not isinstance(value, dict):
        return sanitize_display_text(value)

    preferred_keys = (
        "date",
        "title",
        "subtitle",
        "body",
        "description",
        "source",
        "note",
    )
    parts = [
        sanitize_display_text(value.get(key))
        for key in preferred_keys
        if sanitize_display_text(value.get(key))
    ]
    if parts:
        return " | ".join(parts)

    fallback_parts = [
        sanitize_display_text(item)
        for item in value.values()
        if sanitize_display_text(item)
    ]
    return " | ".join(fallback_parts)


def format_timeline_item(value: object | None) -> str:
    return format_component_item(value)


def coerce_text_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := sanitize_display_text(item))]
    if isinstance(value, str):
        return [cleaned for line in value.splitlines() if (cleaned := sanitize_display_text(line))]
    return []


class PptPreferencesSchema(BaseModel):
    theme: ThemeId = "apple_white"
    slides_limit: int = Field(default=5, ge=1, le=20)
    author: str | None = None

    @field_validator("theme", mode="before")
    @classmethod
    def normalize_theme(cls, value: object) -> ThemeId:
        return normalize_theme_id(value)


class PptDeckCreateRequest(BaseModel):
    type: DeckSourceType
    content: str = Field(min_length=1)
    preferences: PptPreferencesSchema = Field(default_factory=PptPreferencesSchema)

    @model_validator(mode="before")
    @classmethod
    def accept_flat_test_payload(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        raw = dict(value)
        content = raw.get("content") or raw.get("text") or raw.get("input_text") or raw.get("source_text")
        preferences = raw.get("preferences")
        if not isinstance(preferences, dict):
            preferences = {}
        if "theme" not in preferences and ("theme" in raw or "theme_name" in raw):
            preferences["theme"] = raw.get("theme") or raw.get("theme_name")
        if "slides_limit" not in preferences and ("slides_limit" in raw or "slidesLimit" in raw):
            preferences["slides_limit"] = raw.get("slides_limit") or raw.get("slidesLimit")
        if "author" not in preferences and "author" in raw:
            preferences["author"] = raw.get("author")

        return {
            **raw,
            "type": raw.get("type") or "chat_record",
            "content": content,
            "preferences": preferences,
        }


class PptSlideSchema(BaseModel):
    id: str | None = None
    slide_id: str
    layout: SlideLayout = "bullets"
    title: str
    body: list[str] = Field(default_factory=list)
    subtitle: str | None = None
    kicker: str | None = None
    quote: str | None = None
    source: str | None = None
    left_title: str | None = None
    right_title: str | None = None
    left: list[str] = Field(default_factory=list)
    right: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)
    quadrants: list["PptComponentItemSchema"] = Field(default_factory=list)
    blocks: list["PptComponentItemSchema"] = Field(default_factory=list)
    metrics: list["PptMetricSchema"] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    notes: str | None = None
    theme: ThemeId = "apple_white"
    author: str | None = None
    last_modified: str = Field(default_factory=timestamp_now)
    version: int = 1

    @field_validator("theme", mode="before")
    @classmethod
    def normalize_theme(cls, value: object) -> ThemeId:
        return normalize_theme_id(value)

    @field_validator(
        "title",
        "subtitle",
        "kicker",
        "quote",
        "source",
        "left_title",
        "right_title",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: object) -> object:
        if value is None:
            return value
        return sanitize_display_text(value)

    @field_validator("body", "left", "right", "items", "actions", mode="before")
    @classmethod
    def normalize_text_lists(cls, value: object) -> object:
        return coerce_text_list(value)

    @model_validator(mode="after")
    def mirror_slide_ids(self) -> "PptSlideSchema":
        if self.id is None:
            self.id = self.slide_id
        return self


class PptMetricSchema(BaseModel):
    label: str
    value: str
    note: str | None = None

    @field_validator("label", "value", "note", mode="before")
    @classmethod
    def normalize_metric_text(cls, value: object) -> object:
        if value is None:
            return value
        return sanitize_display_text(value)


class PptComponentItemSchema(BaseModel):
    title: str
    body: str | None = None
    subtitle: str | None = None
    source: str | None = None

    @field_validator("title", "body", "subtitle", "source", mode="before")
    @classmethod
    def normalize_component_text(cls, value: object) -> object:
        if value is None:
            return value
        return sanitize_display_text(value)


class PptDeckHistorySchema(BaseModel):
    action: Literal["create", "modify", "export"]
    version: int
    timestamp: str
    summary: str
    instruction: str | None = None


class PptDeckSchema(BaseModel):
    deck_id: str
    type: DeckSourceType
    title: str
    source_content: str
    theme: ThemeId
    author: str | None = None
    version: int = 1
    last_modified: str
    slides: list[PptSlideSchema] = Field(default_factory=list)
    html: str
    history: list[PptDeckHistorySchema] = Field(default_factory=list)


class PptDeckModifyRequest(BaseModel):
    instruction: str = Field(min_length=1)
    current_deck: PptDeckSchema | dict[str, Any] | None = None
    slide_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_instruction_aliases(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        raw = dict(value)
        instruction = (
            raw.get("instruction")
            or raw.get("prompt")
            or raw.get("natural_language")
            or raw.get("text")
        )
        return {
            **raw,
            "instruction": instruction,
            "slide_id": raw.get("slide_id") or raw.get("slideId"),
        }


class PptThemeSchema(BaseModel):
    theme_id: ThemeId
    label: str


class PptExportSchema(BaseModel):
    deck_id: str
    file_name: str
    path: str
    url: str | None = None
    version: int
