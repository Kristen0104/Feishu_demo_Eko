from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.modules.aippt.spec_lock import SpecLock


@dataclass(frozen=True)
class TextBoxSpec:
    box_width: int
    box_height: int
    font_size: int
    line_height: int
    max_lines: int
    max_chars: int
    min_font_size: int


@dataclass(frozen=True)
class FittedText:
    lines: list[str]
    font_size: int
    line_height: int


class AIPPTTemplateRenderer:
    _OBJECTIVE_BOX_SPEC = TextBoxSpec(
        box_width=520,
        box_height=60,
        font_size=20,
        line_height=30,
        max_lines=2,
        max_chars=22,
        min_font_size=16,
    )
    _LEFT_TEXT_BOX_SPEC = TextBoxSpec(
        box_width=500,
        box_height=52,
        font_size=22,
        line_height=26,
        max_lines=2,
        max_chars=16,
        min_font_size=18,
    )
    _CHAPTER_TITLE_BOX_SPEC = TextBoxSpec(
        box_width=360,
        box_height=132,
        font_size=34,
        line_height=42,
        max_lines=3,
        max_chars=11,
        min_font_size=24,
    )
    _RIGHT_PANEL_BOX_SPECS: dict[str, list[TextBoxSpec]] = {
        "three_cards": [
            TextBoxSpec(box_width=364, box_height=56, font_size=18, line_height=22, max_lines=2, max_chars=10, min_font_size=14),
            TextBoxSpec(box_width=364, box_height=56, font_size=18, line_height=22, max_lines=2, max_chars=10, min_font_size=14),
            TextBoxSpec(box_width=364, box_height=56, font_size=18, line_height=22, max_lines=2, max_chars=10, min_font_size=14),
        ],
        "timeline": [
            TextBoxSpec(box_width=96, box_height=40, font_size=16, line_height=20, max_lines=2, max_chars=11, min_font_size=12),
            TextBoxSpec(box_width=96, box_height=40, font_size=16, line_height=20, max_lines=2, max_chars=11, min_font_size=12),
            TextBoxSpec(box_width=96, box_height=40, font_size=16, line_height=20, max_lines=2, max_chars=11, min_font_size=12),
        ],
        "metrics": [
            TextBoxSpec(box_width=122, box_height=44, font_size=16, line_height=18, max_lines=2, max_chars=11, min_font_size=12),
            TextBoxSpec(box_width=122, box_height=44, font_size=16, line_height=18, max_lines=2, max_chars=11, min_font_size=12),
            TextBoxSpec(box_width=332, box_height=46, font_size=16, line_height=20, max_lines=2, max_chars=11, min_font_size=12),
        ],
        "comparison": [
            TextBoxSpec(box_width=292, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=12, min_font_size=12),
            TextBoxSpec(box_width=292, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=12, min_font_size=12),
            TextBoxSpec(box_width=292, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=12, min_font_size=12),
        ],
        "process": [
            TextBoxSpec(box_width=266, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=11, min_font_size=12),
            TextBoxSpec(box_width=266, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=11, min_font_size=12),
            TextBoxSpec(box_width=266, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=11, min_font_size=12),
        ],
        "architecture": [
            TextBoxSpec(box_width=360, box_height=38, font_size=15, line_height=18, max_lines=2, max_chars=14, min_font_size=12),
            TextBoxSpec(box_width=98, box_height=52, font_size=13, line_height=16, max_lines=3, max_chars=16, min_font_size=10),
            TextBoxSpec(box_width=112, box_height=28, font_size=12, line_height=14, max_lines=2, max_chars=10, min_font_size=10),
        ],
        "cover": [
            TextBoxSpec(box_width=268, box_height=44, font_size=18, line_height=22, max_lines=2, max_chars=12, min_font_size=13),
            TextBoxSpec(box_width=268, box_height=44, font_size=18, line_height=22, max_lines=2, max_chars=12, min_font_size=13),
            TextBoxSpec(box_width=268, box_height=44, font_size=18, line_height=22, max_lines=2, max_chars=12, min_font_size=13),
        ],
        "closing": [
            TextBoxSpec(box_width=330, box_height=44, font_size=18, line_height=22, max_lines=2, max_chars=13, min_font_size=13),
            TextBoxSpec(box_width=330, box_height=44, font_size=18, line_height=22, max_lines=2, max_chars=13, min_font_size=13),
            TextBoxSpec(box_width=330, box_height=44, font_size=18, line_height=22, max_lines=2, max_chars=13, min_font_size=13),
        ],
        "toc": [
            TextBoxSpec(box_width=300, box_height=40, font_size=18, line_height=21, max_lines=2, max_chars=13, min_font_size=13),
            TextBoxSpec(box_width=300, box_height=40, font_size=18, line_height=21, max_lines=2, max_chars=13, min_font_size=13),
            TextBoxSpec(box_width=300, box_height=40, font_size=18, line_height=21, max_lines=2, max_chars=13, min_font_size=13),
        ],
        "chapter": [
            TextBoxSpec(box_width=332, box_height=42, font_size=18, line_height=22, max_lines=2, max_chars=13, min_font_size=13),
            TextBoxSpec(box_width=332, box_height=42, font_size=18, line_height=22, max_lines=2, max_chars=13, min_font_size=13),
            TextBoxSpec(box_width=332, box_height=42, font_size=18, line_height=22, max_lines=2, max_chars=13, min_font_size=13),
        ],
        "matrix": [
            TextBoxSpec(box_width=244, box_height=44, font_size=15, line_height=18, max_lines=2, max_chars=14, min_font_size=11),
            TextBoxSpec(box_width=244, box_height=44, font_size=15, line_height=18, max_lines=2, max_chars=14, min_font_size=11),
            TextBoxSpec(box_width=244, box_height=44, font_size=15, line_height=18, max_lines=2, max_chars=14, min_font_size=11),
            TextBoxSpec(box_width=244, box_height=44, font_size=15, line_height=18, max_lines=2, max_chars=14, min_font_size=11),
        ],
        "swimlane": [
            TextBoxSpec(box_width=304, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=12, min_font_size=12),
            TextBoxSpec(box_width=304, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=12, min_font_size=12),
            TextBoxSpec(box_width=304, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=12, min_font_size=12),
        ],
    }

    def __init__(self) -> None:
        self._templates_dir = Path(__file__).resolve().parent / "templates"

    def render(
        self,
        *,
        deck_title: str,
        slide_number: int,
        template_name: str,
        page_title: str,
        objective: str,
        text_box: list[str],
        right_items: list[str],
        accent: str,
        accent_soft: str,
        accent_pale: str,
        spec_lock: SpecLock | None = None,
        background_image_href: str | None = None,
        body_density: str = "standard",
    ) -> str:
        spec_lock = spec_lock or SpecLock()
        colors = self._resolved_colors(spec_lock, accent=accent, accent_soft=accent_soft, accent_pale=accent_pale)
        font_family = spec_lock.font_family("body")
        title_font_family = spec_lock.font_family("title")
        title_size = spec_lock.font_size("title", 34)
        subtitle_size = spec_lock.font_size("subtitle", 20)
        page_rhythm = spec_lock.rhythm_for_slide(slide_number)
        body_profile = self._body_density_profile(body_density)
        template = (self._templates_dir / f"{template_name}.svg").read_text(encoding="utf-8")
        prepared_right_items = (
            self._complete_architecture_items(right_items, text_box, objective)
            if template_name == "architecture"
            else self._complete_right_items(right_items, text_box, objective)
        )
        replacements = {
            "{{ACCENT}}": colors["primary"],
            "{{ACCENT_SOFT}}": colors["accent"],
            "{{ACCENT_PALE}}": colors["secondary_accent"],
            "{{DECK_TITLE}}": self._escape_xml(deck_title),
            "{{SLIDE_NUM}}": f"{slide_number:02d}",
            "{{PAGE_TITLE}}": self._escape_xml(page_title),
            "{{PAGE_TITLE_LINES}}": self._render_fitted_lines(
                self._fit_text_to_box(page_title, spec=self._CHAPTER_TITLE_BOX_SPEC),
                x=80,
                y=198,
                fill="#FFFFFF",
                font_weight="800",
                font_family=title_font_family,
            ),
            "{{OBJECTIVE_LINES}}": self._render_fitted_lines(
                self._fit_text_to_box(objective, spec=body_profile["objective_spec"]),
                x=84,
                y=286,
                fill=colors["text_secondary"],
                font_family=font_family,
            ),
            "{{LEFT_CONTENT}}": self._render_left_points(
                text_box,
                accent=colors["primary"],
                text_color=colors["text_secondary"],
                font_family=font_family,
                spec=body_profile["left_spec"],
                max_points=body_profile["left_points"],
                gap=body_profile["left_gap"],
            ),
            "{{RIGHT_CONTENT}}": self._render_right_panel(
                template_name,
                prepared_right_items,
                colors=colors,
                font_family=font_family,
                page_rhythm=page_rhythm,
            ),
        }
        for key, value in replacements.items():
            template = template.replace(key, value)
        if background_image_href:
            template = self._add_background_image(template, background_image_href)
        template = self._apply_spec_lock_to_template(
            template,
            colors=colors,
            font_family=font_family,
            title_font_family=title_font_family,
            title_size=title_size,
            subtitle_size=subtitle_size,
        )
        return template

    def _add_background_image(self, template: str, href: str) -> str:
        image = (
            f'\n  <image href="{self._escape_xml(href)}" x="0" y="112" width="1280" height="608" '
            'preserveAspectRatio="xMidYMid slice"/>'
            '\n  <rect x="0" y="112" width="1280" height="608" fill="#F8FAFC" fill-opacity="0.84"/>'
        )
        marker = '<rect width="1280" height="720" fill="#F8FAFC"/>'
        if marker in template:
            return template.replace(marker, marker + image, 1)
        return template.replace(">", ">" + image, 1)

    def _resolved_colors(self, spec_lock: SpecLock, *, accent: str, accent_soft: str, accent_pale: str) -> dict[str, str]:
        return {
            "bg": spec_lock.color("bg", "#F8FAFC"),
            "panel": spec_lock.color("panel", "#FFFFFF"),
            "primary": spec_lock.color("primary", accent),
            "accent": spec_lock.color("accent", accent_soft),
            "secondary_accent": spec_lock.color("secondary_accent", accent_pale),
            "text": spec_lock.color("text", "#0F172A"),
            "text_secondary": spec_lock.color("text_secondary", "#475569"),
            "border": spec_lock.color("border", "#E2E8F0"),
        }

    def _apply_spec_lock_to_template(
        self,
        template: str,
        *,
        colors: dict[str, str],
        font_family: str,
        title_font_family: str,
        title_size: int,
        subtitle_size: int,
    ) -> str:
        replacements = {
            'fill="#F8FAFC"': f'fill="{colors["bg"]}"',
            'fill="#FFFFFF"': f'fill="{colors["panel"]}"',
            'fill="#0F172A"': f'fill="{colors["text"]}"',
            'fill="#475569"': f'fill="{colors["text_secondary"]}"',
            'fill="#334155"': f'fill="{colors["text_secondary"]}"',
            'stroke="#E2E8F0"': f'stroke="{colors["border"]}"',
            'font-family="Microsoft YaHei, Arial, sans-serif"': f'font-family="{self._font_attr(font_family)}"',
            'font-size="34"': f'font-size="{title_size}"',
            'font-size="20"': f'font-size="{subtitle_size}"',
        }
        for old, new in replacements.items():
            template = template.replace(old, new)
        body_font_attr = self._font_attr(font_family)
        title_font_attr = self._font_attr(title_font_family)
        template = template.replace(f'<text x="84" y="66" font-family="{body_font_attr}"', f'<text x="84" y="66" font-family="{title_font_attr}"')
        template = template.replace(f'<text x="84" y="184" font-family="{body_font_attr}"', f'<text x="84" y="184" font-family="{title_font_attr}"')
        return template

    def _font_attr(self, font_family: str) -> str:
        return font_family.replace('"', "").replace("'", "")

    def _body_density_profile(self, body_density: str) -> dict[str, object]:
        if body_density == "sparse":
            return {
                "objective_spec": TextBoxSpec(box_width=520, box_height=48, font_size=21, line_height=28, max_lines=2, max_chars=20, min_font_size=17),
                "left_spec": TextBoxSpec(box_width=500, box_height=42, font_size=23, line_height=26, max_lines=2, max_chars=15, min_font_size=19),
                "left_points": 2,
                "left_gap": 86,
            }
        if body_density == "detailed":
            return {
                "objective_spec": TextBoxSpec(box_width=560, box_height=72, font_size=19, line_height=24, max_lines=3, max_chars=24, min_font_size=15),
                "left_spec": TextBoxSpec(box_width=500, box_height=48, font_size=19, line_height=22, max_lines=2, max_chars=20, min_font_size=15),
                "left_points": 4,
                "left_gap": 62,
            }
        if body_density == "dense":
            return {
                "objective_spec": TextBoxSpec(box_width=570, box_height=78, font_size=18, line_height=22, max_lines=3, max_chars=27, min_font_size=14),
                "left_spec": TextBoxSpec(box_width=500, box_height=38, font_size=16, line_height=19, max_lines=2, max_chars=25, min_font_size=12),
                "left_points": 6,
                "left_gap": 45,
            }
        return {
            "objective_spec": self._OBJECTIVE_BOX_SPEC,
            "left_spec": self._LEFT_TEXT_BOX_SPEC,
            "left_points": 3,
            "left_gap": 66,
        }

    def _render_left_points(
        self,
        text_box: list[str],
        *,
        accent: str,
        text_color: str,
        font_family: str,
        spec: TextBoxSpec | None = None,
        max_points: int = 4,
        gap: int = 66,
    ) -> str:
        groups: list[str] = []
        spec = spec or self._LEFT_TEXT_BOX_SPEC
        start_y = 392
        for index, item in enumerate(text_box[:max_points]):
            block_y = start_y + (index * gap)
            fitted = self._fit_text_to_box(item, spec=spec)
            groups.append(f'<circle cx="108" cy="{block_y - 10}" r="7" fill="{accent}"/>')
            groups.append(
                self._render_fitted_lines(
                    fitted,
                    x=132,
                    y=block_y,
                    fill=text_color,
                    font_weight="500",
                    font_family=font_family,
                )
            )
        return "\n  ".join(groups)

    def _render_right_panel(
        self,
        template_name: str,
        items: list[str],
        *,
        colors: dict[str, str],
        font_family: str,
        page_rhythm: str,
    ) -> str:
        if template_name == "three_cards":
            return self._render_three_cards(items, colors=colors, font_family=font_family, page_rhythm=page_rhythm)
        if template_name == "cover":
            return self._render_cover_summary(items, colors=colors, font_family=font_family)
        if template_name == "toc":
            return self._render_toc(items, colors=colors, font_family=font_family)
        if template_name == "chapter":
            return self._render_chapter_marks(items, colors=colors, font_family=font_family)
        if template_name == "closing":
            return self._render_closing_actions(items, colors=colors, font_family=font_family)
        if template_name == "timeline":
            return self._render_timeline(items, colors=colors, font_family=font_family)
        if template_name == "metrics":
            return self._render_metrics(items, colors=colors, font_family=font_family)
        if template_name == "comparison":
            return self._render_comparison(items, colors=colors, font_family=font_family)
        if template_name == "process":
            return self._render_process(items, colors=colors, font_family=font_family)
        if template_name == "architecture":
            return self._render_architecture(items, colors=colors, font_family=font_family)
        if template_name == "matrix":
            return self._render_matrix(items, colors=colors, font_family=font_family)
        if template_name == "swimlane":
            return self._render_swimlane(items, colors=colors, font_family=font_family)
        raise ValueError(f"Unsupported template: {template_name}")

    def _complete_right_items(self, right_items: list[str], text_box: list[str], objective: str) -> list[str]:
        candidates = [*right_items, *text_box, objective]
        completed: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            normalized = " ".join(str(item).split())
            if not normalized or normalized in seen:
                continue
            completed.append(normalized)
            seen.add(normalized)
            if len(completed) == 3:
                return completed
        while len(completed) < 3:
            completed.append(f"关键要点 {len(completed) + 1}")
        return completed

    def _complete_architecture_items(self, right_items: list[str], text_box: list[str], objective: str) -> list[str]:
        candidates = [*right_items, *text_box, objective]
        completed: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            normalized = " ".join(str(item).split())
            if not normalized or normalized in seen:
                continue
            completed.append(normalized)
            seen.add(normalized)
            if len(completed) == 7:
                return completed
        while len(completed) < 7:
            completed.append(f"架构要素 {len(completed) + 1}")
        return completed

    def _render_three_cards(
        self,
        items: list[str],
        *,
        colors: dict[str, str],
        font_family: str,
        page_rhythm: str,
    ) -> str:
        if page_rhythm == "breathing":
            item = items[0]
            fitted = self._fit_text_to_box(
                item,
                spec=TextBoxSpec(
                    box_width=364,
                    box_height=100,
                    font_size=24,
                    line_height=30,
                    max_lines=3,
                    max_chars=13,
                    min_font_size=18,
                ),
            )
            return "\n  ".join(
                [
                    f'<rect x="748" y="296" width="420" height="188" rx="28" fill="{colors["panel"]}"/>',
                    self._render_fitted_lines(
                        fitted,
                        x=778,
                        y=360,
                        fill=colors["text"],
                        font_weight="700",
                        font_family=font_family,
                    ),
                ]
            )
        blocks: list[str] = []
        positions = [(748, 244), (748, 392), (748, 540)]
        specs = self._RIGHT_PANEL_BOX_SPECS["three_cards"]
        for index, item in enumerate(items[:3]):
            x, y = positions[index]
            spec = specs[index]
            fitted = self._fit_text_to_box(item, spec=spec)
            blocks.append(f'<rect x="{x}" y="{y}" width="420" height="116" rx="24" fill="{colors["panel"]}"/>')
            blocks.append(
                self._render_fitted_lines(
                    fitted,
                    x=x + 28,
                    y=y + 48,
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        return "\n  ".join(blocks)

    def _render_cover_summary(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body = [
            f'<text x="820" y="198" font-family="{self._font_attr(font_family)}" font-size="15" font-weight="700" fill="{colors["primary"]}">Executive Briefing</text>',
        ]
        positions = [(820, 278), (820, 374), (820, 470)]
        specs = self._RIGHT_PANEL_BOX_SPECS["cover"]
        for index, item in enumerate(items[:3]):
            y = positions[index][1]
            body.append(f'<circle cx="790" cy="{y - 8}" r="7" fill="{colors["primary"]}"/>')
            fitted = self._fit_text_to_box(item, spec=specs[index])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=positions[index][0],
                    y=y,
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_closing_actions(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body = [
            f'<text x="760" y="210" font-family="{self._font_attr(font_family)}" font-size="15" font-weight="700" fill="{colors["primary"]}">Next Actions</text>',
        ]
        positions = [(760, 292), (760, 394), (760, 496)]
        specs = self._RIGHT_PANEL_BOX_SPECS["closing"]
        for index, item in enumerate(items[:3]):
            x, y = positions[index]
            body.append(f'<rect x="{x}" y="{y - 42}" width="380" height="76" rx="18" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>')
            body.append(f'<rect x="{x}" y="{y - 42}" width="46" height="76" rx="18" fill="{colors["primary"]}"/>')
            body.append(
                f'<text x="{x + 16}" y="{y + 4}" font-family="{self._font_attr(font_family)}" font-size="14" font-weight="800" fill="#FFFFFF">{index + 1}</text>'
            )
            fitted = self._fit_text_to_box(item, spec=specs[index])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=x + 68,
                    y=y - 5,
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_toc(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body: list[str] = []
        positions = [(760, 220), (760, 316), (760, 412)]
        specs = self._RIGHT_PANEL_BOX_SPECS["toc"]
        for index, item in enumerate(items[:3]):
            x, y = positions[index]
            body.append(f'<circle cx="{x}" cy="{y - 8}" r="18" fill="{colors["primary"]}"/>')
            body.append(
                f'<text x="{x - 8}" y="{y - 2}" font-family="{self._font_attr(font_family)}" font-size="13" font-weight="800" fill="#FFFFFF">{index + 1}</text>'
            )
            fitted = self._fit_text_to_box(item, spec=specs[index])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=x + 42,
                    y=y,
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_chapter_marks(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body = [
            f'<text x="744" y="240" font-family="{self._font_attr(font_family)}" font-size="15" font-weight="700" fill="{colors["primary"]}">Section Focus</text>',
        ]
        positions = [(744, 318), (744, 414), (744, 510)]
        specs = self._RIGHT_PANEL_BOX_SPECS["chapter"]
        for index, item in enumerate(items[:3]):
            fitted = self._fit_text_to_box(item, spec=specs[index])
            body.append(f'<rect x="720" y="{positions[index][1] - 42}" width="420" height="72" rx="16" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>')
            body.append(f'<rect x="720" y="{positions[index][1] - 42}" width="8" height="72" rx="4" fill="{colors["primary"]}"/>')
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=positions[index][0],
                    y=positions[index][1],
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_matrix(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        labels = items[:4]
        fallback_labels = ["高影响低成本", "高影响高成本", "低影响低成本", "后续观察"]
        while len(labels) < 4:
            labels.append(fallback_labels[len(labels)])
        body = [
            f'<line x1="632" y1="364" x2="632" y2="574" stroke="{colors["border"]}" stroke-width="2"/>',
            f'<line x1="196" y1="470" x2="1068" y2="470" stroke="{colors["border"]}" stroke-width="2"/>',
            f'<text x="206" y="358" font-family="{self._font_attr(font_family)}" font-size="13" font-weight="700" fill="{colors["primary"]}">Impact</text>',
            f'<text x="994" y="596" font-family="{self._font_attr(font_family)}" font-size="13" font-weight="700" fill="{colors["text_secondary"]}">Effort</text>',
        ]
        cells = [(246, 430), (682, 430), (246, 542), (682, 542)]
        specs = self._RIGHT_PANEL_BOX_SPECS["matrix"]
        for index, label in enumerate(labels[:4]):
            x, y = cells[index]
            body.append(f'<rect x="{x - 28}" y="{y - 54}" width="300" height="82" rx="16" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>')
            fitted = self._fit_text_to_box(label, spec=specs[index])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=x,
                    y=y,
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_swimlane(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body: list[str] = []
        y_positions = [394, 478, 562]
        specs = self._RIGHT_PANEL_BOX_SPECS["swimlane"]
        for index, item in enumerate(items[:3]):
            y = y_positions[index]
            body.append(f'<rect x="150" y="{y - 42}" width="960" height="64" rx="16" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>')
            body.append(f'<rect x="150" y="{y - 42}" width="150" height="64" rx="16" fill="{colors["secondary_accent"]}"/>')
            body.append(
                f'<text x="190" y="{y - 2}" font-family="{self._font_attr(font_family)}" font-size="13" font-weight="800" fill="{colors["primary"]}">Lane {index + 1}</text>'
            )
            fitted = self._fit_text_to_box(item, spec=specs[index])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=330,
                    y=y - 2,
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        body.append(f'<line x1="330" y1="600" x2="1070" y2="600" stroke="{colors["primary"]}" stroke-width="4" stroke-linecap="round"/>')
        return "\n  ".join(body)

    def _render_timeline(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body = [
            f'<line x1="210" y1="452" x2="1054" y2="452" stroke="{colors["primary"]}" stroke-width="6" stroke-linecap="round"/>',
            f'<circle cx="260" cy="452" r="18" fill="{colors["primary"]}"/>',
            f'<circle cx="632" cy="452" r="18" fill="{colors["primary"]}"/>',
            f'<circle cx="1004" cy="452" r="18" fill="{colors["primary"]}"/>',
            f'<rect x="170" y="486" width="210" height="72" rx="18" fill="{colors["panel"]}"/>',
            f'<rect x="526" y="486" width="210" height="72" rx="18" fill="{colors["panel"]}"/>',
            f'<rect x="882" y="486" width="210" height="72" rx="18" fill="{colors["panel"]}"/>',
        ]
        positions = [(198, 528), (554, 528), (910, 528)]
        specs = self._RIGHT_PANEL_BOX_SPECS["timeline"]
        for index, item in enumerate(items[:3]):
            spec = specs[index]
            fitted = self._fit_text_to_box(item, spec=spec)
            x, y = positions[index]
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=x,
                    y=y,
                    fill=colors["text_secondary"],
                    font_weight="600",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_metrics(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body = [
            f'<rect x="130" y="374" width="258" height="120" rx="24" fill="{colors["panel"]}"/>',
            f'<rect x="452" y="374" width="258" height="120" rx="24" fill="{colors["panel"]}"/>',
            f'<rect x="774" y="374" width="258" height="120" rx="24" fill="{colors["panel"]}"/>',
            f'<rect x="160" y="526" width="820" height="48" rx="18" fill="{colors["panel"]}"/>',
            f'<rect x="190" y="540" width="180" height="20" rx="10" fill="{colors["primary"]}"/>',
            f'<rect x="406" y="540" width="250" height="20" rx="10" fill="{colors["accent"]}"/>',
            f'<rect x="692" y="540" width="220" height="20" rx="10" fill="{colors["primary"]}"/>',
        ]
        positions = [
            (160, 426, 18, "700", colors["text"]),
            (482, 426, 18, "700", colors["text"]),
            (804, 426, 18, "700", colors["text"]),
        ]
        specs = self._RIGHT_PANEL_BOX_SPECS["metrics"]
        for index, item in enumerate(items[:3]):
            x, y, _, font_weight, fill = positions[index]
            spec = specs[index]
            fitted = self._fit_text_to_box(item, spec=spec)
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=x,
                    y=y,
                    fill=fill,
                    font_weight=font_weight,
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_comparison(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body = [
            f'<rect x="752" y="248" width="400" height="64" rx="18" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
            f'<rect x="752" y="336" width="400" height="64" rx="18" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
            f'<rect x="752" y="424" width="400" height="64" rx="18" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
            f'<rect x="776" y="268" width="34" height="24" rx="12" fill="{colors["primary"]}"/>',
            f'<rect x="776" y="356" width="34" height="24" rx="12" fill="{colors["accent"]}"/>',
            f'<rect x="776" y="444" width="34" height="24" rx="12" fill="{colors["primary"]}"/>',
        ]
        positions = [(828, 276), (828, 364), (828, 452)]
        labels = ["A", "B", "C"]
        specs = self._RIGHT_PANEL_BOX_SPECS["comparison"]
        for index, item in enumerate(items[:3]):
            body.append(
                f'<text x="787" y="{positions[index][1] + 1}" font-family="{self._font_attr(font_family)}" font-size="13" font-weight="700" fill="#FFFFFF">{labels[index]}</text>'
            )
            fitted = self._fit_text_to_box(item, spec=specs[index])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=positions[index][0],
                    y=positions[index][1],
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_process(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        body = [
            f'<line x1="230" y1="464" x2="1000" y2="464" stroke="{colors["primary"]}" stroke-width="5" stroke-linecap="round"/>',
            f'<circle cx="230" cy="464" r="20" fill="{colors["primary"]}"/>',
            f'<circle cx="615" cy="464" r="20" fill="{colors["primary"]}"/>',
            f'<circle cx="1000" cy="464" r="20" fill="{colors["primary"]}"/>',
            f'<rect x="148" y="386" width="240" height="72" rx="18" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
            f'<rect x="533" y="386" width="240" height="72" rx="18" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
            f'<rect x="918" y="386" width="240" height="72" rx="18" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
        ]
        positions = [(178, 426), (563, 426), (948, 426)]
        specs = self._RIGHT_PANEL_BOX_SPECS["process"]
        for index, item in enumerate(items[:3]):
            number = f"0{index + 1}"
            body.append(
                f'<text x="{[221, 606, 991][index]}" y="469" font-family="{self._font_attr(font_family)}" font-size="12" font-weight="700" fill="#FFFFFF">{number}</text>'
            )
            fitted = self._fit_text_to_box(item, spec=specs[index])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=positions[index][0],
                    y=positions[index][1],
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _render_architecture(self, items: list[str], *, colors: dict[str, str], font_family: str) -> str:
        parent = self._compact_architecture_label(items[0]) if items else "Core System"
        modules = [self._compact_architecture_label(item) for item in (items[1:4] if len(items) >= 4 else items[:3])]
        flow_items = [self._compact_architecture_label(item) for item in (items[4:7] if len(items) >= 7 else modules)]
        while len(modules) < 3:
            modules.append(f"Module {len(modules) + 1}")
        while len(flow_items) < 3:
            flow_items.append(f"Flow {len(flow_items) + 1}")

        parent_fitted = self._fit_text_to_box(parent, spec=self._RIGHT_PANEL_BOX_SPECS["architecture"][0])
        body = [
            f'<rect x="746" y="242" width="424" height="268" rx="18" fill="{colors["secondary_accent"]}" stroke="{colors["primary"]}" stroke-width="2" stroke-dasharray="7 5"/>',
            self._render_fitted_lines(
                parent_fitted,
                x=776,
                y=276,
                fill=colors["primary"],
                font_weight="800",
                font_family=font_family,
            ),
            f'<rect x="768" y="320" width="118" height="104" rx="16" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
            f'<rect x="902" y="320" width="118" height="104" rx="16" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
            f'<rect x="1036" y="320" width="118" height="104" rx="16" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
            f'<line x1="886" y1="372" x2="902" y2="372" stroke="{colors["primary"]}" stroke-width="3" stroke-linecap="round"/>',
            f'<line x1="1020" y1="372" x2="1036" y2="372" stroke="{colors["primary"]}" stroke-width="3" stroke-linecap="round"/>',
        ]
        module_positions = [(784, 364), (918, 364), (1052, 364)]
        for index, module in enumerate(modules[:3]):
            badge_x = module_positions[index][0]
            badge_fill = colors["primary"] if index != 1 else colors["accent"]
            body.append(f'<rect x="{badge_x}" y="340" width="34" height="24" rx="12" fill="{badge_fill}"/>')
            body.append(
                f'<text x="{badge_x + 10}" y="357" font-family="{self._font_attr(font_family)}" font-size="11" font-weight="800" fill="#FFFFFF">0{index + 1}</text>'
            )
            fitted = self._fit_text_to_box(module, spec=self._RIGHT_PANEL_BOX_SPECS["architecture"][1])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=module_positions[index][0],
                    y=module_positions[index][1] + 28,
                    fill=colors["text"],
                    font_weight="700",
                    font_family=font_family,
                )
            )

        body.extend(
            [
                f'<rect x="768" y="452" width="386" height="38" rx="12" fill="{colors["panel"]}" stroke="{colors["border"]}" stroke-width="1"/>',
                f'<line x1="802" y1="471" x2="1120" y2="471" stroke="{colors["text_secondary"]}" stroke-width="1" stroke-dasharray="4 3"/>',
            ]
        )
        flow_positions = [(784, 476), (918, 476), (1052, 476)]
        for index, flow in enumerate(flow_items[:3]):
            fitted = self._fit_text_to_box(flow, spec=self._RIGHT_PANEL_BOX_SPECS["architecture"][2])
            body.append(
                self._render_fitted_lines(
                    fitted,
                    x=flow_positions[index][0],
                    y=flow_positions[index][1],
                    fill=colors["text_secondary"],
                    font_weight="600",
                    font_family=font_family,
                )
            )
        return "\n  ".join(body)

    def _compact_architecture_label(self, text: str) -> str:
        normalized = " ".join(str(text).split())
        if not normalized or any(self._is_cjk(char) for char in normalized):
            return normalized
        phrase_replacements = {
            "PPT Master Exporter": "PPT Export",
            "PPT Master Export": "PPT Export",
            "AI PPT Generation Pipeline": "AI PPT Gen. Pipe.",
        }
        for source, target in phrase_replacements.items():
            normalized = normalized.replace(source, target)
        replacements = {
            "Generation": "Gen.",
            "Pipeline": "Pipe.",
            "Orchestrator": "Orch.",
            "Builder": "Build",
            "Exporter": "Export",
            "Export": "Exp.",
            "Recommendation": "Rec.",
            "Architecture": "Arch.",
            "Application": "App",
            "Database": "DB",
            "Service": "Svc",
            "Processing": "Process",
            "Editable": "Edit.",
        }
        compacted = normalized
        for source, target in replacements.items():
            compacted = compacted.replace(source, target)
        return compacted

    def _render_fitted_lines(
        self,
        fitted: FittedText,
        *,
        x: int,
        y: int,
        fill: str,
        font_weight: str = "400",
        font_family: str = '"Microsoft YaHei", Arial, sans-serif',
    ) -> str:
        return self._render_lines(
            fitted.lines,
            x=x,
            y=y,
            line_height=fitted.line_height,
            font_size=fitted.font_size,
            fill=fill,
            font_weight=font_weight,
            font_family=font_family,
        )

    def _render_lines(
        self,
        lines: list[str],
        *,
        x: int,
        y: int,
        line_height: int,
        font_size: int,
        fill: str,
        font_weight: str = "400",
        font_family: str = '"Microsoft YaHei", Arial, sans-serif',
    ) -> str:
        return "\n  ".join(
            f'<text x="{x}" y="{y + (index * line_height)}" font-family="{self._font_attr(font_family)}" font-size="{font_size}" font-weight="{font_weight}" fill="{fill}">{self._escape_xml(line)}</text>'
            for index, line in enumerate(lines)
        )

    def _fit_text_to_box(
        self,
        text: str,
        *,
        spec: TextBoxSpec,
    ) -> FittedText:
        normalized = " ".join(text.replace("\n", " ").split())
        if not normalized:
            return FittedText(lines=[""], font_size=spec.font_size, line_height=spec.line_height)

        # Phase 1: retain original char/line heuristics as a coarse constraint.
        candidate = self._pre_clip_text(normalized, max_chars=spec.max_chars, max_lines=spec.max_lines)

        # Phase 2: verify by real-size estimate; shrink font to safe floor if needed.
        for font_size in range(spec.font_size, spec.min_font_size - 1, -1):
            line_height = max(12, round(spec.line_height * (font_size / spec.font_size)))
            fitted = self._fit_with_fixed_font(candidate, spec=spec, font_size=font_size, line_height=line_height)
            if self._lines_fit_box(
                fitted.lines,
                box_width=spec.box_width,
                box_height=spec.box_height,
                font_size=font_size,
                line_height=line_height,
            ):
                return fitted

        return self._fit_with_fixed_font(
            candidate,
            spec=spec,
            font_size=spec.min_font_size,
            line_height=max(12, round(spec.line_height * (spec.min_font_size / spec.font_size))),
        )

    def _fit_with_fixed_font(self, text: str, *, spec: TextBoxSpec, font_size: int, line_height: int) -> FittedText:
        candidate = text
        while True:
            lines = self._wrap_text_to_width(
                candidate,
                box_width=spec.box_width,
                font_size=font_size,
                max_lines=spec.max_lines,
            )
            if self._lines_fit_box(
                lines,
                box_width=spec.box_width,
                box_height=spec.box_height,
                font_size=font_size,
                line_height=line_height,
            ):
                return FittedText(lines=lines, font_size=font_size, line_height=line_height)
            if len(candidate) <= 1:
                safe_lines = lines[: spec.max_lines] or [""]
                return FittedText(lines=safe_lines, font_size=font_size, line_height=line_height)
            candidate = candidate[:-1].rstrip()

    def _pre_clip_text(self, text: str, *, max_chars: int, max_lines: int) -> str:
        chars_limit = max(1, max_chars * max_lines)
        if len(text) <= chars_limit:
            return text
        return text[:chars_limit].rstrip()

    def _wrap_text_to_width(
        self,
        text: str,
        *,
        box_width: int,
        font_size: int,
        max_lines: int,
    ) -> list[str]:
        normalized = " ".join(text.replace("\n", " ").split())
        if not normalized:
            return [""]
        chunks: list[str] = []
        current = ""
        current_width = 0.0
        for char in normalized:
            width = self._char_width(char, font_size)
            if current and current_width + width > box_width:
                chunks.append(current.strip())
                current = char
                current_width = width
            else:
                current += char
                current_width += width
        if current:
            chunks.append(current.strip())
        if len(chunks) > max_lines:
            chunks = chunks[:max_lines]
            chunks[-1] = chunks[-1][: max(1, len(chunks[-1]))].rstrip()
        return chunks or [normalized[:1]]

    def _lines_fit_box(
        self,
        lines: list[str],
        *,
        box_width: int,
        box_height: int,
        font_size: int,
        line_height: int,
    ) -> bool:
        if len(lines) * line_height > box_height:
            return False
        return all(sum(self._char_width(char, font_size) for char in line) <= box_width for line in lines)

    def _char_width(self, char: str, font_size: int) -> float:
        if char.isspace():
            return font_size * 0.28
        if self._is_cjk(char):
            return font_size * 0.96
        if char.isdigit():
            return font_size * 0.58
        if char.isupper():
            return font_size * 0.62
        if char.islower():
            return font_size * 0.56
        return font_size * 0.36

    def _is_cjk(self, char: str) -> bool:
        code = ord(char)
        return (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0x3040 <= code <= 0x30FF
            or 0xAC00 <= code <= 0xD7AF
        )

    def _escape_xml(self, value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
