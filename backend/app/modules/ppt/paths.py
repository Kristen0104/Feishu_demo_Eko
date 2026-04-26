"""Path helpers for the bundled ppt-master vendor copy."""

from __future__ import annotations

from pathlib import Path


def resolve_ppt_master_root() -> Path:
    """Find the local vendored ppt-master checkout."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        for candidate in (
            parent / "vendor" / "ppt_master",
            parent / "backend" / "vendor" / "ppt_master",
            parent / "skills" / "ppt-master",
        ):
            if candidate.exists():
                return candidate
    return here.parents[0] / "vendor" / "ppt_master"

