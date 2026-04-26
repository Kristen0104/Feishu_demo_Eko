"""Import and catalogue template packs derived from reference PPTX files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..modules.ppt import TemplateImportService


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GENERATED_ROOT = BACKEND_ROOT / "generated"
DEFAULT_TEMPLATES_ROOT = BACKEND_ROOT / "vendor" / "ppt_master" / "templates" / "layouts"
DEFAULT_CATALOG_PATH = DEFAULT_TEMPLATES_ROOT / "layouts_index.json"


@dataclass(frozen=True)
class TemplatePackSummary:
    pack_dir: Path
    source_pptx: Path
    base_template: str
    manifest_path: Path


class PptTemplateService:
    def __init__(
        self,
        generated_root: str | Path = DEFAULT_GENERATED_ROOT,
        templates_root: str | Path = DEFAULT_TEMPLATES_ROOT,
        catalog_path: str | Path = DEFAULT_CATALOG_PATH,
        importer: TemplateImportService | None = None,
    ):
        self.generated_root = Path(generated_root)
        self.templates_root = Path(templates_root)
        self.catalog_path = Path(catalog_path)
        self.importer = importer or TemplateImportService(
            repo_root=REPO_ROOT,
            generated_root=self.generated_root,
            templates_root=self.templates_root,
            catalog_path=self.catalog_path,
        )

    def import_sources(
        self,
        source_paths: list[str],
        collection_name: str | None = None,
        preferred_template: str | None = None,
        style_group: str | None = None,
    ) -> list[TemplatePackSummary]:
        results = self.importer.import_sources(
            source_paths=source_paths,
            collection_name=collection_name,
            preferred_template=preferred_template,
            style_group=style_group,
        )
        return [
            TemplatePackSummary(
                pack_dir=item.pack_dir,
                source_pptx=item.source_pptx,
                base_template=item.base_template,
                manifest_path=item.manifest_path,
            )
            for item in results
        ]

    def list_packs(self) -> list[dict[str, Any]]:
        root = self.generated_root / "template_packs"
        if not root.exists():
            return []

        packs: list[dict[str, Any]] = []
        for manifest_path in root.glob("**/template_pack.json"):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            packs.append(
                {
                    "pack_dir": str(manifest_path.parent),
                    "base_template": data.get("base_template"),
                    "style_group": data.get("style_group"),
                    "source_pptx": data.get("source_pptx"),
                    "slides_analyzed": data.get("slides_analyzed"),
                    "created_at": data.get("created_at"),
                }
            )
        return sorted(packs, key=lambda item: item.get("created_at") or "", reverse=True)


ppt_template_service = PptTemplateService()
