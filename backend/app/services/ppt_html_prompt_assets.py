from __future__ import annotations

from pathlib import Path


class PptHtmlPromptAssets:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or (
            Path(__file__).resolve().parent.parent
            / "modules"
            / "ppt"
            / "assets"
            / "guizang"
        )

    def load(self) -> dict[str, str]:
        return {
            "skill_md": self._read_text("SKILL.md"),
            "license_text": self._read_text("LICENSE"),
            "template_html": self._read_text("template.html"),
            "layouts_md": self._read_text("references/layouts.md"),
            "themes_md": self._read_text("references/themes.md"),
            "components_md": self._read_text("references/components.md"),
            "checklist_md": self._read_text("references/checklist.md"),
            "motion_js": self._read_text("assets/motion.min.js"),
        }

    def _read_text(self, relative_path: str) -> str:
        return (self._root / relative_path).read_text(encoding="utf-8")
