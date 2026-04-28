from __future__ import annotations

from app.services.ppt_html_prompt_assets import PptHtmlPromptAssets


def test_ppt_prompt_assets_load_all_vendored_sources() -> None:
    assets = PptHtmlPromptAssets().load()

    assert "guizang-ppt-skill" in assets["skill_md"]
    assert 'id="deck"' in assets["template_html"]
    assert "页面布局库（Layouts）" in assets["layouts_md"]
    assert "主题色预设（Themes）" in assets["themes_md"]
    assert "组件参考 · Components" in assets["components_md"]
    assert "质量检查清单（Checklist）" in assets["checklist_md"]


def test_ppt_prompt_assets_include_supporting_files() -> None:
    assets = PptHtmlPromptAssets().load()

    assert "MIT License" in assets["license_text"]
    assert "motion = await import('./assets/motion.min.js');" in assets["template_html"]
    assert "fitAllSlideFrames" in assets["template_html"]
    assert len(assets["motion_js"]) > 1000
