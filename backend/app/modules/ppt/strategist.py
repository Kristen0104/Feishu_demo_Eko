from __future__ import annotations

import re

from .models import DeckPagePlan, DeckPlan, DeckRequest


def build_deck_plan(request: DeckRequest) -> DeckPlan:
    planning_text = request.raw_prompt.strip() or request.chat_history.strip()
    page_count = _derive_page_count(planning_text)
    template_id = _resolve_template_id(request)
    project_name = _derive_project_name(planning_text)
    product_name = _derive_product_name(planning_text)

    if product_name == "iPhone Air":
        pages = _build_iphone_air_pages(product_name)[:page_count]
    else:
        pages = _build_generic_pages(product_name, page_count)

    return DeckPlan(
        project_name=project_name,
        template_id=template_id,
        pages=pages,
    )


def _resolve_template_id(request: DeckRequest) -> str | None:
    template = request.template_preference.strip()
    if template and template != "auto":
        return template

    text = request.raw_prompt.lower()
    if any(keyword in request.raw_prompt for keyword in ("苹果", "发布会", "浅色")):
        return "google_style"
    if any(keyword in text for keyword in ("apple", "keynote", "launch")):
        return "google_style"
    return None


def _derive_project_name(raw_prompt: str) -> str:
    for pattern in (r"iphone\s*air", r"iphoneair"):
        if re.search(pattern, raw_prompt, flags=re.IGNORECASE):
            return "iphone_air_launch"
    return "ppt_test"


def _derive_product_name(raw_prompt: str) -> str:
    if re.search(r"iphone\s*air|iphoneair", raw_prompt, flags=re.IGNORECASE):
        return "iPhone Air"
    cleaned = re.sub(r"\s*\d+\s*页\s*", " ", raw_prompt, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bppt\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(请|帮我)?生成(一份)?", "", cleaned).strip(" ：:-")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "Presentation"


def _derive_page_count(raw_prompt: str) -> int:
    match = re.search(r"(\d+)\s*页", raw_prompt)
    if not match:
        return 8
    return max(1, min(int(match.group(1)), 8))


def _build_iphone_air_pages(product_name: str) -> tuple[DeckPagePlan, ...]:
    return (
        DeckPagePlan(1, product_name, "cover", "anchor", "苹果发布会浅色主题版 | 轻盈登场"),
        DeckPagePlan(2, "今日内容", "toc", "anchor", "产品定位 | 设计语言 | 显示体验 | 性能与续航 | 拍照与日常场景 | 发布收束"),
        DeckPagePlan(3, "设计理念", "chapter", "anchor", "更轻 | 更薄 | 更像一台 iPhone Air"),
        DeckPagePlan(4, "超薄机身", "content", "dense", "一体化机身语言 | 更轻的握持负担 | 更适合高频随身使用"),
        DeckPagePlan(5, "显示与交互", "content", "dense", "高亮通透的显示效果 | 更顺滑的日常浏览 | 单手操作依然从容"),
        DeckPagePlan(6, "性能与续航", "content", "dense", "轻薄和性能保持平衡 | 应用切换与多任务流畅 | 续航覆盖一整天的使用场景"),
        DeckPagePlan(7, "拍照与日常场景", "content", "breathing", "通勤会议旅行都适合 | 快速记录生活瞬间 | 更轻松的随手创作"),
        DeckPagePlan(8, "谢谢", "ending", "anchor", "iPhone Air | 轻到刚刚好"),
    )


def _build_generic_pages(topic: str, page_count: int) -> tuple[DeckPagePlan, ...]:
    pages: list[DeckPagePlan] = [
        DeckPagePlan(1, topic, "cover", "anchor", f"{topic} | 内容提案"),
        DeckPagePlan(2, "内容概览", "toc", "anchor", "背景与目标 | 方案亮点 | 实施路径 | 价值总结"),
    ]
    content_slots = [
        ("背景与目标", "问题背景 | 目标用户 | 当前机会"),
        ("方案亮点", "核心能力 | 差异化体验 | 关键卖点"),
        ("实施路径", "推进步骤 | 资源准备 | 关键节点"),
        ("价值总结", "业务价值 | 用户收益 | 下一步行动"),
        ("发布建议", "演示节奏 | 风险提示 | 收尾表达"),
    ]

    use_chapter = page_count >= 5
    next_index = 3
    if use_chapter:
        pages.append(DeckPagePlan(next_index, "核心信息", "chapter", "anchor", f"{topic} | 核心内容展开"))
        next_index += 1

    remaining_slots = max(0, page_count - len(pages) - 1)
    for slot_title, slot_brief in content_slots[:remaining_slots]:
        rhythm = "breathing" if slot_title == "价值总结" else "dense"
        pages.append(DeckPagePlan(next_index, slot_title, "content", rhythm, slot_brief))
        next_index += 1

    pages.append(DeckPagePlan(next_index, "谢谢", "ending", "anchor", f"{topic} | 感谢聆听"))
    return tuple(pages[:page_count])
