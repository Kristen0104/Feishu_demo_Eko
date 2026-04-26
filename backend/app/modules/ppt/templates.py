"""PPT-compatible SVG templates and validation."""

from __future__ import annotations

import html
import re
from collections import defaultdict
from typing import Any

from .config import DesignConfig, load_config


FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"<\s*mask\b", "mask"),
    (r"<\s*style\b", "style"),
    (r"\sclass\s*=", "class attribute"),
    (r"<\s*foreignObject\b", "foreignObject"),
    (r"<\s*textPath\b", "textPath"),
    (r"@font-face", "@font-face"),
    (r"<\s*animate\w*\b", "SVG animation"),
    (r"<\s*script\b", "script"),
    (r"rgba\s*\(", "rgba color"),
    (r"<\s*g\b[^>]*\sopacity\s*=", "group opacity"),
    (r"<\s*symbol\b", "symbol"),
    (r"<\s*use\b(?![^>]*\bdata-icon\s*=)", "use without data-icon"),
)


def validate_svg(svg: str) -> None:
    """Reject SVG features known to break the ppt-master conversion pipeline."""
    for pattern, label in FORBIDDEN_PATTERNS:
        if re.search(pattern, svg, flags=re.IGNORECASE):
            raise ValueError(f"SVG contains forbidden PPT-incompatible markup: {label}")

    if not re.search(r"<svg\b[^>]*viewBox\s*=\s*['\"]0 0 (1280 720|1024 768|1242 1660|1080 1080|1080 1920)['\"]", svg):
        raise ValueError("SVG must declare a supported viewBox")


class SafeFormatDict(defaultdict):
    def __missing__(self, key: str) -> str:
        return ""


class TemplateLibrary:
    """Small set of placeholder-based SVG layouts."""

    def __init__(self, config: DesignConfig | None = None):
        self.config = config or load_config()
        self.templates = _build_templates(self.config)

    def has_layout(self, layout: str) -> bool:
        return layout in self.templates

    def render(self, page: dict[str, Any]) -> str:
        layout = str(page.get("layout") or "content")
        if layout not in self.templates:
            raise KeyError(f"Unknown aippt layout: {layout}")

        values = self._prepare_values(page)
        svg = self.templates[layout].format_map(SafeFormatDict(str, values))
        validate_svg(svg)
        return svg

    def _prepare_values(self, page: dict[str, Any]) -> dict[str, str]:
        values = {
            "title": _escape(page.get("title", "")),
            "subtitle": _escape(page.get("subtitle", "")),
            "section": _escape(page.get("section", "")),
            "body": _escape(page.get("body", page.get("text", ""))),
            "points": self._render_points(page.get("content", page.get("points", []))),
            "footer": _escape(page.get("footer", "")),
        }

        for key, value in page.items():
            if key not in values and isinstance(value, (str, int, float)):
                values[key] = _escape(value)
        return values

    def _render_points(self, content: Any) -> str:
        if isinstance(content, str):
            items = [line.strip() for line in content.splitlines() if line.strip()]
        elif isinstance(content, list):
            items = [str(item).strip() for item in content if str(item).strip()]
        else:
            items = []

        return "\n".join(
            f'<circle cx="122" cy="{212 + index * 64}" r="6" fill="{self.config.colors["secondary"]}" />'
            f'<text x="146" y="{220 + index * 64}" fill="{self.config.colors["primary"]}" '
            f'font-size="24" font-family="{self.config.fonts["body"]}">{_escape(item)}</text>'
            for index, item in enumerate(items[:7])
        )


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _build_templates(config: DesignConfig) -> dict[str, str]:
    colors = config.colors
    fonts = config.fonts
    view_box = config.canvas.view_box

    return {
        "cover": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" width="{config.canvas.width}" height="{config.canvas.height}">
<rect x="0" y="0" width="{config.canvas.width}" height="{config.canvas.height}" fill="{colors["background"]}" />
<rect x="78" y="76" width="1124" height="568" rx="34" fill="{colors["surface"]}" />
<rect x="78" y="76" width="18" height="568" rx="9" fill="{colors["secondary"]}" />
<text x="136" y="302" fill="{colors["primary"]}" font-size="68" font-weight="700" font-family="{fonts["title"]}">{{title}}</text>
<text x="140" y="364" fill="{colors["muted"]}" font-size="28" font-family="{fonts["body"]}">{{subtitle}}</text>
<text x="140" y="584" fill="{colors["secondary"]}" font-size="18" font-family="{fonts["body"]}">{{footer}}</text>
</svg>''',
        "toc": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" width="{config.canvas.width}" height="{config.canvas.height}">
<rect x="0" y="0" width="{config.canvas.width}" height="{config.canvas.height}" fill="{colors["background"]}" />
<text x="88" y="120" fill="{colors["primary"]}" font-size="46" font-weight="700" font-family="{fonts["title"]}">{{title}}</text>
<rect x="88" y="154" width="180" height="8" rx="4" fill="{colors["accent"]}" />
{{points}}
</svg>''',
        "chapter": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" width="{config.canvas.width}" height="{config.canvas.height}">
<rect x="0" y="0" width="{config.canvas.width}" height="{config.canvas.height}" fill="{colors["primary"]}" />
<circle cx="1012" cy="154" r="96" fill="{colors["accent"]}" fill-opacity="0.32" />
<text x="96" y="248" fill="{colors["accent"]}" font-size="24" font-family="{fonts["body"]}">{{section}}</text>
<text x="96" y="352" fill="#FFFFFF" font-size="60" font-weight="700" font-family="{fonts["title"]}">{{title}}</text>
<text x="100" y="414" fill="#FFFFFF" fill-opacity="0.72" font-size="24" font-family="{fonts["body"]}">{{subtitle}}</text>
</svg>''',
        "content": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" width="{config.canvas.width}" height="{config.canvas.height}">
<rect x="0" y="0" width="{config.canvas.width}" height="{config.canvas.height}" fill="{colors["background"]}" />
<text x="86" y="104" fill="{colors["primary"]}" font-size="42" font-weight="700" font-family="{fonts["title"]}">{{title}}</text>
<rect x="86" y="136" width="1108" height="456" rx="28" fill="{colors["surface"]}" />
{{points}}
<text x="88" y="650" fill="{colors["muted"]}" font-size="16" font-family="{fonts["body"]}">{{footer}}</text>
</svg>''',
        "ending": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" width="{config.canvas.width}" height="{config.canvas.height}">
<rect x="0" y="0" width="{config.canvas.width}" height="{config.canvas.height}" fill="{colors["primary"]}" />
<rect x="374" y="186" width="532" height="268" rx="34" fill="#FFFFFF" fill-opacity="0.08" />
<text x="640" y="312" text-anchor="middle" fill="#FFFFFF" font-size="58" font-weight="700" font-family="{fonts["title"]}">{{title}}</text>
<text x="640" y="372" text-anchor="middle" fill="#FFFFFF" fill-opacity="0.76" font-size="24" font-family="{fonts["body"]}">{{subtitle}}</text>
</svg>''',
    }
