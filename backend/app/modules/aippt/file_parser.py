from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class FileParser:
    def __init__(self, vendor_root: Path) -> None:
        self._vendor_root = vendor_root
        self._scripts_root = vendor_root / "skills" / "ppt-master" / "scripts" / "source_to_md"

    def parse_input_file(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix in {".md", ".txt"}:
            return file_path.read_text(encoding="utf-8")
        if suffix == ".pdf":
            return self._run_script("pdf_to_md.py", file_path)
        if suffix in {".docx", ".doc", ".html", ".htm", ".epub"}:
            return self._run_script("doc_to_md.py", file_path)
        if suffix in {".ppt", ".pptx", ".ppsx"}:
            return self._run_script("ppt_to_md.py", file_path)
        raise ValueError(f"Unsupported file type: {suffix}")

    def parse_source_url(self, source_url: str, output_file: Path) -> str:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        self._run_command(
            [
                sys.executable,
                str(self._scripts_root / "web_to_md.py"),
                source_url,
                "-o",
                str(output_file),
            ]
        )
        return output_file.read_text(encoding="utf-8")

    def _run_script(self, script_name: str, input_file: Path) -> str:
        output_file = input_file.with_suffix(".md")
        self._run_command(
            [
                sys.executable,
                str(self._scripts_root / script_name),
                str(input_file),
                "-o",
                str(output_file),
            ]
        )
        return output_file.read_text(encoding="utf-8")

    def _run_command(self, command: list[str]) -> None:
        result = subprocess.run(
            command,
            cwd=self._vendor_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "source parsing failed"
            raise RuntimeError(message)
