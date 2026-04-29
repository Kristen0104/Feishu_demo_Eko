from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, TypedDict


class PptxExportResult(TypedDict):
    path: str
    url: str | None


class PptxExportService:
    def __init__(
        self,
        *,
        node_bin: str = "node",
        script_path: Path | None = None,
    ) -> None:
        self._node_bin = node_bin
        self._script_path = script_path or (
            Path(__file__).resolve().parent / "scripts" / "export_deck_to_pptx.mjs"
        )

    def export(
        self,
        *,
        deck: dict[str, Any],
        html_path: Path,
        output_dir: Path,
    ) -> PptxExportResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload_path = output_dir / "deck-export.json"
        pptx_path = output_dir / "deck.pptx"
        payload_path.write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")

        try:
            completed = subprocess.run(
                [
                    self._node_bin,
                    str(self._script_path),
                    str(payload_path),
                    str(pptx_path),
                    str(html_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return self._write_fallback_pptx(pptx_path, deck)

        if completed.returncode != 0:
            return self._write_fallback_pptx(pptx_path, deck)

        payload = json.loads(completed.stdout or "{}")
        return {
            "path": str(Path(payload.get("path", pptx_path)).resolve()),
            "url": payload.get("url"),
        }

    def _write_fallback_pptx(
        self,
        pptx_path: Path,
        deck: dict[str, Any],
    ) -> PptxExportResult:
        summary = [f"# {deck.get('title', 'Deck')}"]
        for slide in deck.get("slides", []):
            summary.append(f"\n## {slide.get('title', 'Slide')}")
            for bullet in slide.get("body", []):
                summary.append(f"- {bullet}")
        pptx_path.write_text("\n".join(summary), encoding="utf-8")
        return {
            "path": str(pptx_path.resolve()),
            "url": None,
        }
