"""PPT generation service that bridges FastAPI and aippt."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GENERATED_ROOT = BACKEND_ROOT / "generated"
DEFAULT_SCRIPTS_DIR = BACKEND_ROOT / "vendor" / "ppt_master" / "scripts"
DEFAULT_TEMPLATE_ROOT = BACKEND_ROOT / "vendor" / "ppt_master" / "templates" / "layouts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ..modules.ppt import AipptGenerator
from ..modules.ppt.project_builder import build_project_artifacts


@dataclass(frozen=True)
class PptGenerationResult:
    project_name: str
    project_path: Path
    output_path: Path
    result_url: str


class PptGenerationService:
    def __init__(
        self,
        generated_root: str | Path = DEFAULT_GENERATED_ROOT,
        scripts_dir: str | Path = DEFAULT_SCRIPTS_DIR,
        generator_factory: Callable[..., AipptGenerator] = AipptGenerator,
    ):
        self.generated_root = Path(generated_root)
        self.scripts_dir = Path(scripts_dir)
        self.generator_factory = generator_factory

    async def generate(self, content: dict[str, Any]) -> PptGenerationResult:
        self._validate_content(content)
        self._ensure_scripts_available()

        project_name = str(content.get("project_name") or "aippt")
        template_dir = self._resolve_template_dir(content)
        project_slug = _slug(project_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_path = self.generated_root / "ppt" / f"{project_slug}_{timestamp}"
        output_path = project_path / "exports" / f"{project_slug}_{timestamp}.pptx"

        project_path.mkdir(parents=True, exist_ok=True)
        deck_plan = content.get("deck_plan")
        if deck_plan is not None:
            build_project_artifacts(project_path, deck_plan)
        generator = self.generator_factory(
            workspace=project_path,
            scripts_dir=self.scripts_dir,
            template_dir=template_dir,
        )
        generated_path = await generator.generate(content, output_path)

        result_url = "/" + generated_path.relative_to(self.generated_root).as_posix()
        return PptGenerationResult(
            project_name=project_name,
            project_path=project_path,
            output_path=generated_path,
            result_url=f"/generated{result_url}",
        )

    def _ensure_scripts_available(self) -> None:
        required = ("total_md_split.py", "finalize_svg.py", "svg_to_pptx.py")
        missing = [name for name in required if not (self.scripts_dir / name).exists()]
        if missing:
            missing_text = ", ".join(missing)
            raise FileNotFoundError(
                f"ppt-master scripts are missing in {self.scripts_dir}: {missing_text}. "
                "Install the vendored ppt-master under backend/vendor/ppt_master or configure scripts_dir."
            )

    def _validate_content(self, content: dict[str, Any]) -> None:
        pages = content.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError("content.pages must be a non-empty list")
        for index, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                raise ValueError(f"content.pages[{index}] must be an object")

    def _resolve_template_dir(self, content: dict[str, Any]) -> Path | None:
        template_dir = content.get("template_dir")
        if template_dir:
            path = Path(str(template_dir))
            if path.exists():
                return path
            raise FileNotFoundError(f"template_dir not found: {path}")

        template_name = content.get("template_name")
        if template_name:
            path = DEFAULT_TEMPLATE_ROOT / str(template_name)
            if path.exists():
                return path
            raise FileNotFoundError(f"template_name not found: {template_name}")

        return None


def _slug(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", text).strip("_")
    return text or "aippt"


ppt_generation_service = PptGenerationService()
