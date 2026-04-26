"""Main async PPT generation pipeline."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .api_client import ApiClient
from .config import DesignConfig, load_config
from .executor import should_use_template_direct_render
from .paths import resolve_ppt_master_root
from .template_pack import TemplatePack
from .templates import TemplateLibrary, validate_svg


class AipptGenerator:
    def __init__(
        self,
        config_path: str | Path | None = None,
        workspace: str | Path = ".",
        scripts_dir: str | Path | None = None,
        template_dir: str | Path | None = None,
        max_concurrency: int = 10,
        api: ApiClient | None = None,
        env: dict[str, str] | None = None,
    ):
        if max_concurrency < 1 or max_concurrency > 10:
            raise ValueError("max_concurrency must be between 1 and 10")

        self.workspace = Path(workspace)
        self.config: DesignConfig = load_config(config_path)
        self.template_dir = Path(template_dir) if template_dir else None
        self.templates = TemplatePack.from_dir(self.template_dir) if self.template_dir else TemplateLibrary(self.config)
        self.api = api or ApiClient()
        self.max_concurrency = max_concurrency
        self.svg_output_dir = self.workspace / "svg_output"
        self.svg_final_dir = self.workspace / "svg_final"
        self.notes_dir = self.workspace / "notes"
        self.exports_dir = self.workspace / "exports"
        self.scripts_dir = Path(scripts_dir) if scripts_dir else resolve_ppt_master_root() / "scripts"
        self.env = env or {}

    async def generate(self, content: dict[str, Any], output_path: str | Path | None = None) -> Path:
        """Generate SVG pages, run ppt-master post-processing, and return PPTX path."""
        output = Path(output_path) if output_path else self._default_output_path(content)
        await self.generate_svg_assets(content)
        await self._run_pipeline(output)
        return output

    async def generate_svg_assets(self, content: dict[str, Any]) -> list[Path]:
        pages = list(content.get("pages") or [])
        if not pages:
            raise ValueError("content must include at least one page")

        self.svg_output_dir.mkdir(parents=True, exist_ok=True)
        self.svg_final_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def render_one(index: int, page: dict[str, Any]) -> tuple[int, str]:
            async with semaphore:
                svg = await self.render_template(page)
                validate_svg(svg)
                return index, svg

        rendered = await asyncio.gather(*[
            render_one(index, page) for index, page in enumerate(pages, start=1)
        ])

        paths: list[Path] = []
        for index, svg in sorted(rendered, key=lambda item: item[0]):
            page = pages[index - 1]
            path = self.svg_output_dir / f"slide_{index:02d}_{_slug(page.get('layout') or page.get('title') or 'page')}.svg"
            path.write_text(svg, encoding="utf-8")
            paths.append(path)

        self._write_total_notes(paths, pages)

        manifest = {
            "project_name": content.get("project_name", "aippt"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "pages": [str(path.name) for path in paths],
        }
        (self.workspace / "aippt_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return paths

    async def render_template(self, page: dict[str, Any]) -> str:
        layout = str(page.get("layout") or "content")
        page_type = str(page.get("page_type") or layout)
        page_rhythm = str(page.get("page_rhythm") or ("anchor" if page_type in {"cover", "toc", "chapter", "ending"} else "dense"))
        if self.templates.has_layout(layout) and should_use_template_direct_render(page_type, page_rhythm):
            return self.templates.render_direct(page)

        design_context = {
            "canvas": self.config.canvas.__dict__,
            "colors": self.config.colors,
            "fonts": self.config.fonts,
            "spacing": self.config.spacing,
        }
        return await self.api.generate_svg(page, design_context)

    async def _run_pipeline(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        for script_name, args in (
            ("svg_quality_checker.py", []),
            ("total_md_split.py", []),
            ("finalize_svg.py", []),
            ("svg_to_pptx.py", ["-s", "final", "-o", str(output_path)]),
        ):
            await self._run_script(script_name, args, output_path)

        if not output_path.exists():
            raise RuntimeError(
                f"PPTX pipeline finished but did not create {output_path}. "
                "Check ppt-master svg_to_pptx.py output arguments or AIPPT_OUTPUT_PATH support."
            )

    async def _run_script(self, script_name: str, args: list[str], output_path: Path) -> None:
        script = self.scripts_dir / script_name
        if not script.exists():
            raise FileNotFoundError(
                f"Missing required ppt-master script: {script}. "
                "Place the vendored ppt-master under backend/vendor/ppt_master/scripts or pass scripts_dir=..."
            )

        env = {
            **os.environ,
            **self.env,
            "AIPPT_WORKSPACE": str(self.workspace),
            "AIPPT_SVG_OUTPUT_DIR": str(self.svg_output_dir),
            "AIPPT_SVG_FINAL_DIR": str(self.svg_final_dir),
            "AIPPT_OUTPUT_PATH": str(output_path),
        }
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script),
            str(self.workspace),
            *args,
            cwd=str(self.workspace),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                f"{script_name} failed with exit code {process.returncode}\n"
                f"stdout:\n{stdout.decode(errors='replace')}\n"
                f"stderr:\n{stderr.decode(errors='replace')}"
            )

    def _default_output_path(self, content: dict[str, Any]) -> Path:
        project_name = _slug(content.get("project_name") or "aippt")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.exports_dir / f"{project_name}_{timestamp}.pptx"

    def _write_total_notes(self, svg_paths: list[Path], pages: list[dict[str, Any]]) -> None:
        sections: list[str] = []
        for svg_path, page in zip(svg_paths, pages):
            note = page.get("notes") or page.get("speaker_notes") or page.get("content") or page.get("body") or page.get("title") or ""
            if isinstance(note, list):
                note_text = "\n".join(f"- {item}" for item in note)
            else:
                note_text = str(note)
            sections.append(f"# {svg_path.stem}\n\n{note_text.strip() or svg_path.stem}")

        (self.notes_dir / "total.md").write_text("\n\n---\n\n".join(sections) + "\n", encoding="utf-8")


def _slug(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", text).strip("_")
    return text or "page"
