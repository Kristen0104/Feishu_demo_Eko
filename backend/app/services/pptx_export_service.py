from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import TypedDict

from app.config import get_settings


class PptxExportResult(TypedDict):
    pptx_path: str
    slide_image_paths: list[str]


class PptxExportService:
    def __init__(
        self,
        *,
        node_bin: str | None = None,
        node_modules: str | None = None,
        viewport_width: int | None = None,
        viewport_height: int | None = None,
        device_scale_factor: int | None = None,
        script_path: Path | None = None,
    ) -> None:
        settings = get_settings()
        self._node_bin = node_bin or settings.PPT_EXPORT_NODE_BIN
        self._node_modules = node_modules or settings.PPT_EXPORT_NODE_MODULES
        self._viewport_width = viewport_width or settings.PPT_EXPORT_VIEWPORT_WIDTH
        self._viewport_height = viewport_height or settings.PPT_EXPORT_VIEWPORT_HEIGHT
        self._device_scale_factor = (
            device_scale_factor or settings.PPT_EXPORT_DEVICE_SCALE_FACTOR
        )
        self._script_path = script_path or (
            Path(__file__).resolve().parent / "scripts" / "export_html_to_pptx.mjs"
        )

    def export(
        self,
        *,
        html_path: Path,
        output_dir: Path,
        deck_title: str,
    ) -> PptxExportResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        pptx_path = output_dir / "deck.pptx"
        cmd = [
            self._node_bin,
            str(self._script_path),
            "--html",
            str(html_path),
            "--output-dir",
            str(output_dir),
            "--pptx",
            str(pptx_path),
            "--title",
            deck_title,
            "--width",
            str(self._viewport_width),
            "--height",
            str(self._viewport_height),
            "--device-scale-factor",
            str(self._device_scale_factor),
        ]
        env = os.environ.copy()
        if self._node_modules:
            env["NODE_PATH"] = self._node_modules
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "Unknown export error"
            raise RuntimeError(f"PPTX export failed: {detail}")

        payload = json.loads(completed.stdout)
        return {
            "pptx_path": payload["pptxPath"],
            "slide_image_paths": payload["slideImagePaths"],
        }
