from __future__ import annotations

from pathlib import Path

from .models import DeckPlan
from .spec_lock import render_spec_lock


def build_project_artifacts(project_dir: Path, plan: DeckPlan) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "design_spec.md").write_text(
        _render_design_spec(plan),
        encoding="utf-8",
    )
    (project_dir / "spec_lock.md").write_text(
        render_spec_lock(plan),
        encoding="utf-8",
    )


def _render_design_spec(plan: DeckPlan) -> str:
    page_lines = [
        f"| **Project Name** | {plan.project_name} |",
        "| **Canvas Format** | PPT 16:9 (1280x720) |",
        f"| **Page Count** | {len(plan.pages)} |",
        "| **Design Style** | Apple keynote inspired light launch deck |",
        "| **Target Audience** | Product launch audience |",
        "| **Use Case** | Product release presentation |",
    ]
    outline_lines = [
        f"{page.index}. **{page.title}** ({page.page_type}, {page.page_rhythm}) - {page.brief}"
        for page in plan.pages
    ]
    return (
        f"# {plan.project_name} - Design Spec\n\n"
        "## I. Project Information\n\n"
        "| Item | Value |\n"
        "| ---- | ----- |\n"
        + "\n".join(page_lines)
        + "\n\n"
        "## II. Canvas Specification\n\n"
        "| Property | Value |\n"
        "| -------- | ----- |\n"
        "| **Format** | PPT 16:9 |\n"
        "| **Dimensions** | 1280x720 |\n"
        "| **viewBox** | `0 0 1280 720` |\n\n"
        "## III. Visual Theme\n\n"
        f"- **Template**: {plan.template_id or 'free-design'}\n"
        "- **Theme**: Light theme\n"
        "- **Tone**: Modern product launch\n\n"
        "## IX. Content Outline\n\n"
        + "\n".join(outline_lines)
        + "\n"
    )
