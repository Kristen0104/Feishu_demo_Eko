"""Batch import of reference PPTX files into reusable template packs."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree as ET

from .paths import resolve_ppt_master_root
from .template_matcher import infer_template_name, load_layout_catalog


@dataclass(frozen=True)
class ImportedTemplatePack:
    source_pptx: Path
    pack_dir: Path
    base_template: str
    manifest_path: Path
    source_manifest_path: Path


class TemplateImportService:
    def __init__(
        self,
        repo_root: str | Path,
        generated_root: str | Path,
        templates_root: str | Path,
        catalog_path: str | Path,
        importer_script: str | Path | None = None,
        manifest_loader: Callable[[Path], dict[str, Any]] | None = None,
    ):
        self.repo_root = Path(repo_root)
        self.generated_root = Path(generated_root)
        self.templates_root = Path(templates_root)
        self.catalog_path = Path(catalog_path)
        self.catalog = load_layout_catalog(catalog_path)
        self.importer_script = Path(importer_script) if importer_script else resolve_ppt_master_root() / "scripts" / "pptx_template_import.py"
        self.manifest_loader = manifest_loader or self._load_manifest

    def import_sources(
        self,
        source_paths: list[str | Path],
        collection_name: str | None = None,
        preferred_template: str | None = None,
        style_group: str | None = None,
    ) -> list[ImportedTemplatePack]:
        if not source_paths:
            raise ValueError("source_paths must not be empty")

        style_group_slug = _slug(style_group) if style_group else None
        collection_slug = _slug(collection_name or f"template_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        collection_dir = self.generated_root / "template_packs"
        if style_group_slug:
            collection_dir = collection_dir / style_group_slug
        collection_dir = collection_dir / collection_slug
        collection_dir.mkdir(parents=True, exist_ok=True)

        results: list[ImportedTemplatePack] = []
        for index, source in enumerate(source_paths, start=1):
            results.append(
                self._import_one(
                    source_path=Path(source),
                    collection_dir=collection_dir,
                    preferred_template=preferred_template,
                    style_group=style_group_slug,
                    variant_index=index,
                )
            )

        (collection_dir / "collection.json").write_text(
            json.dumps(
                {
                    "collection_name": collection_slug,
                    "style_group": style_group_slug,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "packs": [
                        {
                            "source_pptx": str(item.source_pptx),
                            "pack_dir": str(item.pack_dir),
                            "base_template": item.base_template,
                            "manifest_path": str(item.manifest_path),
                        }
                        for item in results
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return results

    def _import_one(
        self,
        source_path: Path,
        collection_dir: Path,
        preferred_template: str | None,
        style_group: str | None,
        variant_index: int,
    ) -> ImportedTemplatePack:
        if not source_path.exists():
            raise FileNotFoundError(f"Source PPTX not found: {source_path}")
        if source_path.suffix.lower() != ".pptx":
            raise ValueError(f"Expected .pptx source, got: {source_path.name}")

        source_slug = _slug(source_path.stem)
        source_import_dir = collection_dir / f"{source_slug}_import"
        variant_name = _build_variant_name(style_group, source_slug, preferred_template, variant_index)
        pack_dir = collection_dir / variant_name
        source_import_dir.mkdir(parents=True, exist_ok=True)
        pack_dir.mkdir(parents=True, exist_ok=True)

        manifest = self._run_importer(source_path, source_import_dir)
        source_svg_dir = source_import_dir / "svg"
        source_assets_dir = source_import_dir / "assets"
        if not source_svg_dir.exists():
            raise FileNotFoundError(f"Source SVG directory not found: {source_svg_dir}")

        source_svgs = sorted(source_svg_dir.glob("*.svg"))
        if not source_svgs:
            raise FileNotFoundError(f"No SVG slides found in {source_svg_dir}")

        # Keep the source export as reference material only.
        reference_dir = pack_dir / "reference_svg"
        reference_dir.mkdir(parents=True, exist_ok=True)
        for svg_path in source_svgs:
            shutil.copy2(svg_path, reference_dir / svg_path.name)
        if source_assets_dir.exists():
            shutil.copytree(source_assets_dir, reference_dir / "assets", dirs_exist_ok=True)

        base_template = (
            preferred_template
            or _guess_template_from_style(style_group)
            or infer_template_name(manifest, self.catalog)
        )
        template_source_dir = self.templates_root / base_template
        if not template_source_dir.exists():
            raise FileNotFoundError(f"Template family not found: {template_source_dir}")
        shutil.copytree(template_source_dir, pack_dir, dirs_exist_ok=True)

        source_manifest_path = source_import_dir / "manifest.json"
        manifest_out = {
            "source_pptx": str(source_path),
            "base_template": base_template,
            "style_group": style_group,
            "source_manifest": str(source_manifest_path),
            "slides_analyzed": len(manifest.get("slides", [])),
            "theme": manifest.get("theme", {}),
            "page_type_candidates": manifest.get("pageTypeCandidates", {}),
            "reference_svg_dir": str(reference_dir),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        (pack_dir / "template_pack.json").write_text(
            json.dumps(manifest_out, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return ImportedTemplatePack(
            source_pptx=source_path,
            pack_dir=pack_dir,
            base_template=base_template,
            manifest_path=pack_dir / "template_pack.json",
            source_manifest_path=source_manifest_path,
        )

    def _run_importer(self, source_path: Path, output_dir: Path) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        if not self.importer_script.exists():
            raise FileNotFoundError(f"pptx_template_import.py not found: {self.importer_script}")

        completed = self._run_importer_command(source_path, output_dir, manifest_only=False)
        if completed.returncode != 0:
            completed = self._run_importer_command(source_path, output_dir, manifest_only=True)
        if completed.returncode != 0:
            raise RuntimeError(
                "pptx_template_import.py failed\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        return self.manifest_loader(output_dir)

    def _run_importer_command(self, source_path: Path, output_dir: Path, manifest_only: bool) -> subprocess.CompletedProcess[str]:
        args = [
            sys.executable,
            str(self.importer_script),
            str(source_path),
            "-o",
            str(output_dir),
        ]
        if manifest_only:
            args.append("--manifest-only")
        return subprocess.run(
            args,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def _load_manifest(output_dir: Path) -> dict[str, Any]:
        path = output_dir / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"manifest.json not found in {output_dir}")
        return json.loads(path.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", text).strip("_")
    return text or "template_pack"


def _build_variant_name(
    style_group: str | None,
    source_slug: str,
    preferred_template: str | None,
    variant_index: int,
) -> str:
    parts = [f"variant_{variant_index:02d}"]
    if style_group:
        parts.append(style_group)
    parts.append(source_slug)
    if preferred_template:
        parts.append(preferred_template)
    return _slug("_".join(parts))


LAYOUT_TO_FILE_NAME = {
    "cover": "01_cover.svg",
    "toc": "02_toc.svg",
    "chapter": "02_chapter.svg",
    "content": "03_content.svg",
    "ending": "04_ending.svg",
}


def _select_layout_sources(manifest: dict[str, Any], svg_files: list[Path]) -> dict[str, Path]:
    slides = manifest.get("slides", [])
    svg_by_index = {index: svg_path for index, svg_path in enumerate(svg_files, start=1)}

    def pick(page_types: tuple[str, ...], fallback_indexes: list[int]) -> Path:
        for slide in slides:
            index = slide.get("index")
            if not isinstance(index, int):
                continue
            if str(slide.get("pageType") or "") in page_types and index in svg_by_index:
                return svg_by_index[index]
        for index in fallback_indexes:
            if index in svg_by_index:
                return svg_by_index[index]
        return svg_files[0]

    total = len(svg_files)
    return {
        "cover": pick(("cover_candidate",), [1]),
        "toc": pick(("toc_candidate",), [2, 1]),
        "chapter": pick(("chapter_candidate",), [3, 2, 1]),
        "content": pick(("content_candidate",), [3, 2, 1]),
        "ending": pick(("ending_candidate",), [total, max(total - 1, 1)]),
    }


def _guess_template_from_style(style_group: str | None) -> str | None:
    if not style_group:
        return None
    text = style_group.lower()
    if "学术" in text or "academic" in text:
        return "academic_defense"
    if "咨询" in text or "strategy" in text or "consult" in text:
        return "mckinsey"
    if "政府" in text or "政务" in text or "government" in text:
        return "government_blue"
    return None


SVG_NAMESPACE = "http://www.w3.org/2000/svg"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NAMESPACE)
ET.register_namespace("xlink", XLINK_NAMESPACE)


def _prepare_template_svg(svg_path: Path, layout: str) -> None:
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError:
        text = svg_path.read_text(encoding="utf-8")
        text = re.sub(r"<mask\b.*?</mask>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<use\b[^>]*\/>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"\s(?:xlink:)?href=\"#.*?\"", "", text)
        text = _replace_raw_text_with_placeholders(text, layout)
        svg_path.write_text(text, encoding="utf-8")
        return

    forbidden_tags = {
        "mask",
        "style",
        "foreignObject",
        "textPath",
        "script",
        "symbol",
        "use",
    }

    for parent in root.iter():
        for child in list(parent):
            tag = _local_name(child.tag)
            if tag in forbidden_tags or tag.startswith("animate"):
                parent.remove(child)
                continue
            child.attrib.pop("mask", None)
            child.attrib.pop("class", None)
            if tag == "g":
                child.attrib.pop("opacity", None)

    _rewrite_text_placeholders(root, layout)
    ET.ElementTree(root).write(svg_path, encoding="unicode", xml_declaration=False)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _replace_raw_text_with_placeholders(text: str, layout: str) -> str:
    placeholders = _placeholder_sequence_for_layout(layout)
    for placeholder in placeholders:
        text = re.sub(r">[^<]*<", f">{placeholder}<", text, count=1)
    return text


def _placeholder_sequence_for_layout(layout: str) -> list[str]:
    if layout == "cover":
        return ["{{TITLE}}", "{{SUBTITLE}}", "{{DATE}}", "{{AUTHOR}}"]
    if layout == "chapter":
        return ["{{CHAPTER_TITLE}}", "{{CHAPTER_NUM}}", "{{SUBTITLE}}"]
    if layout == "ending":
        return ["{{THANK_YOU}}", "{{SUBTITLE}}", "{{CONTACT_INFO}}"]
    if layout == "toc":
        return ["{{PAGE_TITLE}}", "{{CONTENT_AREA}}"]
    return ["{{PAGE_TITLE}}", "{{CONTENT_AREA}}"]


def _rewrite_text_placeholders(root: ET.Element, layout: str) -> None:
    text_nodes: list[tuple[ET.Element, float, int, int]] = []
    for index, elem in enumerate(root.iter()):
        if _local_name(elem.tag) != "text":
            continue
        text_nodes.append((elem, _text_font_size(elem), _text_char_count(elem), index))

    if not text_nodes:
        return

    text_nodes.sort(key=lambda item: (-item[1], -item[2], item[3]))
    placeholders = _placeholder_sequence_for_layout(layout)
    if layout in {"content", "toc"} and len(text_nodes) > 1:
        placeholder_order = [placeholders[0], placeholders[1]] + [""] * (len(text_nodes) - 2)
    else:
        placeholder_order = placeholders + [""] * max(0, len(text_nodes) - len(placeholders))

    for (elem, _, _, _), placeholder in zip(text_nodes, placeholder_order):
        _set_text_element_text(elem, placeholder)


def _set_text_element_text(elem: ET.Element, text: str) -> None:
    for child in list(elem):
        elem.remove(child)
    elem.text = text


def _text_font_size(elem: ET.Element) -> float:
    raw = elem.get("font-size")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _text_char_count(elem: ET.Element) -> int:
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in elem.iter():
        if child is elem:
            continue
        if child.text:
            parts.append(child.text)
    return len("".join(parts).strip())
