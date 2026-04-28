from __future__ import annotations

import re
from textwrap import dedent

from app.config import get_settings
from app.services.llm_client import LlmClient
from app.services.ppt_html_prompt_assets import PptHtmlPromptAssets
from app.services.ppt_html_validator import validate_generated_html


class PptHtmlGenerateService:
    def __init__(
        self,
        assets: PptHtmlPromptAssets | None = None,
        llm_client: LlmClient | None = None,
        *,
        allow_live_llm: bool = False,
        llm_timeout_seconds: int | None = None,
        llm_max_tokens: int | None = None,
    ) -> None:
        self._assets = assets or PptHtmlPromptAssets()
        self._llm_client = llm_client or LlmClient()
        self._allow_live_llm = allow_live_llm
        self._llm_timeout_seconds = llm_timeout_seconds or get_settings().PPT_LLM_TIMEOUT_SECONDS
        self._llm_max_tokens = llm_max_tokens or get_settings().PPT_LLM_MAX_TOKENS

    def generate_html(self, *, topic: str, prompt: str, title: str | None = None) -> str:
        bundled_assets = self._assets.load()
        fallback_html = self._build_fallback_html(
            template_html=bundled_assets["template_html"],
            title=title or topic,
        )

        html = fallback_html
        if self._allow_live_llm and self._llm_client.is_configured():
            generated = self._llm_client.complete(
                system_prompt=self._build_system_prompt(bundled_assets),
                user_prompt=self._build_user_prompt(
                    topic=topic,
                    prompt=prompt,
                    title=title,
                ),
                timeout=self._llm_timeout_seconds,
                max_tokens=self._llm_max_tokens,
            ).strip()
            generated = self._strip_code_fences(generated)
            html = self._normalize_generated_output(
                generated=generated,
                template_html=bundled_assets["template_html"],
                title=title or topic,
            )

        report = validate_generated_html(html)
        if not report.is_valid:
            joined_errors = "; ".join(report.errors)
            raise ValueError(f"Generated HTML failed validation: {joined_errors}")
        return html

    def _build_system_prompt(self, assets: dict[str, str]) -> str:
        return "\n\n".join(
            [
                "You generate a complete single-file HTML presentation deck.",
                "Follow the vendored guizang magazine PPT style and reuse its structure instead of inventing a new one.",
                "Prioritize keeping the template shell, CSS, scripts, navigation, and animation system intact.",
                "Return raw HTML only. Do not wrap the response in Markdown fences.",
                assets["skill_md"],
                assets["layouts_md"],
                assets["themes_md"],
            ]
        )

    def _build_user_prompt(
        self,
        *,
        topic: str,
        prompt: str,
        title: str | None,
    ) -> str:
        requested_title = title or topic
        page_instruction = self._resolve_page_count_instruction(prompt)
        return dedent(
            f"""
            Topic: {topic}
            Title: {requested_title}
            User prompt:
            {prompt}

            The server already owns the vendored HTML shell, CSS, JS, navigation, and background effects.
            You should return only the slide markup that belongs inside <div id="deck">.
            {page_instruction}
            Keep the deck concise and presentation-first: one strong idea per slide, avoid overcrowded grids unless the user explicitly asks for dense comparison.
            Keep each slide readable inside a single 16:9 viewport.
            Do not return <!DOCTYPE>, <html>, <head>, <body>, or <div id="deck">.
            Do not use Markdown fences or explanations.
            """
        ).strip()

    def _build_fallback_html(self, *, template_html: str, title: str) -> str:
        return template_html.replace(
            "[必填] 替换为 PPT 标题 · Deck Title",
            title,
            1,
        )

    def _normalize_generated_output(
        self,
        *,
        generated: str,
        template_html: str,
        title: str,
    ) -> str:
        generated = self._repair_common_markup_issues(generated)
        if "<!DOCTYPE html>" in generated and "<html" in generated:
            return self._repair_common_markup_issues(generated)
        return self._inject_slides_into_template(
            template_html=template_html,
            slides_markup=generated,
            title=title,
        )

    def _inject_slides_into_template(
        self,
        *,
        template_html: str,
        slides_markup: str,
        title: str,
    ) -> str:
        html = self._build_fallback_html(template_html=template_html, title=title)
        if "<!-- SLIDES_HERE -->" in html:
            return html.replace("<!-- SLIDES_HERE -->", slides_markup.strip(), 1)

        pattern = r'(<div id="deck">\s*)(.*?)(\s*</div>)'
        replaced, count = re.subn(
            pattern,
            lambda match: f"{match.group(1)}{slides_markup.strip()}{match.group(3)}",
            html,
            count=1,
            flags=re.DOTALL,
        )
        if count:
            return replaced
        return html

    def _strip_code_fences(self, html: str) -> str:
        stripped = html.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            return "\n".join(lines[1:-1]).strip()
        return stripped

    def _repair_common_markup_issues(self, html: str) -> str:
        # Repair a common LLM formatting mistake: an unclosed class attribute like
        # `class="stat-note>...`, which collapses sibling cards into one malformed block.
        repaired = re.sub(r'class="([^"\n<>]*)>', r'class="\1">', html)
        return repaired

    def _resolve_page_count_instruction(self, prompt: str) -> str:
        explicit_count_patterns = [
            r"\b(\d+)\s*-\s*(\d+)\s*(?:页|张|slides|pages)\b",
            r"(\d+)\s*(?:页|张)",
            r"(?:做|生成|输出|写|整理)?\s*(\d+)\s*(?:slides|slide|pages|page)\b",
        ]
        for pattern in explicit_count_patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if not match:
                continue
            if len(match.groups()) == 2 and match.group(2):
                return (
                    "Output exactly the user-requested slide-count range: "
                    f"{match.group(1)}-{match.group(2)} complete "
                    '<section class="slide ...">...</section> blocks.'
                )
            return (
                "Output exactly the user-requested slide count: "
                f"{match.group(1)} complete "
                '<section class="slide ...">...</section> blocks.'
            )

        return 'Output 8-10 complete <section class="slide ...">...</section> blocks.'
