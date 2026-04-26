"""Intent classification helpers."""

from __future__ import annotations

import re


# TODO(PRD-2.1): replace keyword rules with structured intent classification that uses recent conversation context.
INTENT_KEYWORDS = {
    "PPT": [
        "ppt",
        "powerpoint",
        "演示文稿",
        "幻灯片",
        "生成ppt",
        "做ppt",
        "制作ppt",
        "生成演示",
        "生成幻灯片",
        "deck",
        "slides",
    ],
    "DOC": [
        "文档",
        "文稿",
        "方案",
        "报告",
        "撰写",
        "写一个",
        "生成文档",
        "word",
        "生成word",
        "整理成文档",
        "输出文档",
        "形成文档",
    ],
    "SUMMARY": [
        "总结",
        "摘要",
        "概括",
        "提炼",
        "汇总",
        "归纳",
        "整理要点",
        "核心观点",
        "主要结论",
        "归纳一下",
    ],
}


def recognize_intent(message: str) -> str:
    """Recognize a simple chat intent from a message."""
    msg_lower = message.lower()

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in msg_lower:
                return intent

    if any(phrase in message for phrase in ["根据", "基于", "按照", "依据"]):
        if any(word in message for word in ["上文", "前文", "刚才", "讨论", "内容"]):
            for intent, keywords in INTENT_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in msg_lower:
                        return intent

    return "CHAT"


def extract_intent_keywords(message: str) -> dict:
    """Extract keyword hits for debugging and telemetry."""
    msg_lower = message.lower()
    matched = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        hits = [kw for kw in keywords if kw.lower() in msg_lower]
        if hits:
            matched[intent] = hits
    return matched

