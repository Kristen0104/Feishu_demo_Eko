from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SpecLock:
    canvas: dict[str, str] = field(default_factory=dict)
    colors: dict[str, str] = field(default_factory=dict)
    typography: dict[str, str] = field(default_factory=dict)
    page_rhythm: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""

    @classmethod
    def from_file(cls, path: Path) -> "SpecLock":
        return cls.from_text(path.read_text(encoding="utf-8"))

    @classmethod
    def from_text(cls, text: str) -> "SpecLock":
        sections: dict[str, dict[str, str]] = {}
        current_section = ""

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("## "):
                current_section = line[3:].strip()
                sections.setdefault(current_section, {})
                continue
            if not current_section or not line.startswith("- ") or ":" not in line:
                continue

            key, value = line[2:].split(":", 1)
            sections[current_section][key.strip()] = value.strip()

        return cls(
            canvas=sections.get("canvas", {}),
            colors=sections.get("colors", {}),
            typography=sections.get("typography", {}),
            page_rhythm=sections.get("page_rhythm", {}),
            raw_text=text,
        )

    def color(self, role: str, fallback: str) -> str:
        return self.colors.get(role, fallback)

    def font_family(self, role: str = "font") -> str:
        if role == "title":
            return self.typography.get("title_family") or self.typography.get("font_family") or '"Microsoft YaHei", Arial, sans-serif'
        if role == "body":
            return self.typography.get("body_family") or self.typography.get("font_family") or '"Microsoft YaHei", Arial, sans-serif'
        return self.typography.get("font_family") or '"Microsoft YaHei", Arial, sans-serif'

    def font_size(self, role: str, fallback: int) -> int:
        raw_value = self.typography.get(role)
        if raw_value is None:
            return fallback
        try:
            return int(raw_value)
        except ValueError:
            return fallback

    def rhythm_for_slide(self, slide_number: int) -> str:
        return self.page_rhythm.get(f"P{slide_number:02d}", "dense")
