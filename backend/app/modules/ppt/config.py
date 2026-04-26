"""Design configuration for aippt decks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CanvasConfig:
    width: int = 1280
    height: int = 720
    view_box: str = "0 0 1280 720"


@dataclass(frozen=True)
class DesignConfig:
    canvas: CanvasConfig = field(default_factory=CanvasConfig)
    colors: dict[str, str] = field(default_factory=lambda: {
        "background": "#F7F3EA",
        "surface": "#FFFFFF",
        "primary": "#173B45",
        "secondary": "#D95F43",
        "muted": "#667085",
        "accent": "#F4B942",
    })
    fonts: dict[str, str] = field(default_factory=lambda: {
        "title": "Microsoft YaHei, Arial, Calibri",
        "body": "Microsoft YaHei, Arial, Calibri",
    })
    spacing: dict[str, int] = field(default_factory=lambda: {
        "page_x": 84,
        "page_y": 64,
        "gap": 28,
    })

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DesignConfig":
        canvas_data = data.get("canvas", {})
        canvas = CanvasConfig(
            width=int(canvas_data.get("width", 1280)),
            height=int(canvas_data.get("height", 720)),
            view_box=str(canvas_data.get("view_box", canvas_data.get("viewBox", "0 0 1280 720"))),
        )
        default = cls(canvas=canvas)
        return cls(
            canvas=canvas,
            colors={**default.colors, **dict(data.get("colors", {}))},
            fonts={**default.fonts, **dict(data.get("fonts", {}))},
            spacing={**default.spacing, **{k: int(v) for k, v in dict(data.get("spacing", {})).items()}},
        )


def load_config(config_path: str | Path | None = None) -> DesignConfig:
    """Load JSON/YAML-like design config, falling back to safe defaults."""
    path = Path(config_path) if config_path else Path(__file__).with_name("design.yaml")
    if not path.exists():
        return DesignConfig()

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return DesignConfig()

    if path.suffix.lower() == ".json":
        return DesignConfig.from_mapping(json.loads(raw))

    return DesignConfig.from_mapping(_parse_simple_yaml(raw))


def _parse_simple_yaml(raw: str) -> dict[str, Any]:
    """Parse the small nested YAML shape used by aippt without adding PyYAML."""
    result: dict[str, Any] = {}
    current_section: str | None = None

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not line.startswith((" ", "\t")) and stripped.endswith(":"):
            current_section = stripped[:-1]
            result[current_section] = {}
            continue

        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        parsed = _parse_scalar(value.strip())
        if current_section and line.startswith((" ", "\t")):
            result.setdefault(current_section, {})[key.strip()] = parsed
        else:
            result[key.strip()] = parsed
            current_section = None

    return result


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.isdigit():
        return int(value)
    return value
