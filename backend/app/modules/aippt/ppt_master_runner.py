from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


class PPTMasterRunner:
    def __init__(self, vendor_root: Path) -> None:
        self._vendor_root = vendor_root
        self._scripts_dir = vendor_root / "skills" / "ppt-master" / "scripts"

    def export(self, project_dir: Path) -> Path:
        self._ensure_vendor_layout()
        self._run_script("total_md_split.py", project_dir)
        self._run_script("finalize_svg.py", project_dir)
        self._run_script("svg_to_pptx.py", project_dir, "-s", "final")

        exports_dir = project_dir / "exports"
        pptx_files = sorted(
            exports_dir.glob("*.pptx"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not pptx_files:
            raise RuntimeError("PPT Master export finished without creating a PPTX file.")
        return pptx_files[0]

    def validate_svg_output(self, project_dir: Path) -> None:
        self._ensure_vendor_layout()
        self._run_script("svg_quality_checker.py", project_dir, "--format", "ppt169")

    def _ensure_vendor_layout(self) -> None:
        required = [
            self._scripts_dir / "total_md_split.py",
            self._scripts_dir / "finalize_svg.py",
            self._scripts_dir / "svg_to_pptx.py",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise RuntimeError(f"PPT Master scripts are missing: {missing}")

    def _run_script(self, script_name: str, project_dir: Path, *extra_args: str) -> None:
        command = [
            sys.executable,
            str(self._scripts_dir / script_name),
            str(project_dir),
            *extra_args,
        ]
        result = subprocess.run(
            command,
            cwd=self._vendor_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            message = stderr or stdout or f"{script_name} exited with {result.returncode}"
            raise RuntimeError(f"PPT Master script failed: {message}")

    @staticmethod
    def copy_export(source: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination
