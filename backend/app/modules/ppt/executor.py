from __future__ import annotations


def should_use_template_direct_render(page_type: str, page_rhythm: str) -> bool:
    return page_rhythm == "anchor" and page_type in {"cover", "toc", "chapter", "ending"}
