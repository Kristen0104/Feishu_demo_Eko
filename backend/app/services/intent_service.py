"""Compatibility wrapper for the intent module."""

from __future__ import annotations

from ..modules.intent import INTENT_KEYWORDS, extract_intent_keywords, recognize_intent

__all__ = ["INTENT_KEYWORDS", "extract_intent_keywords", "recognize_intent"]

