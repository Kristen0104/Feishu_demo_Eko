from __future__ import annotations

from app.services.ppt_html_validator import validate_generated_html


def test_validate_generated_html_accepts_complete_deck() -> None:
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>Deck Title</title>
</head>
<body>
  <div id="deck">
    <section class="slide hero dark">
      <h1 data-anim>封面</h1>
    </section>
  </div>
</body>
</html>
"""

    report = validate_generated_html(html)

    assert report.is_valid is True
    assert report.errors == []
    assert report.warnings == []


def test_validate_generated_html_rejects_missing_required_structure() -> None:
    html = """<html>
<head></head>
<body>
  <div>missing deck</div>
</body>
</html>
"""

    report = validate_generated_html(html)

    assert report.is_valid is False
    assert any("DOCTYPE" in error for error in report.errors)
    assert any("<title>" in error for error in report.errors)
    assert any('id="deck"' in error for error in report.errors)
    assert any('class="slide' in error for error in report.errors)


def test_validate_generated_html_reports_soft_warnings() -> None:
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>[必填] Deck Title</title>
</head>
<body>
  <div id="deck">
    <section class="slide light">
      <h1>普通页</h1>
    </section>
  </div>
</body>
</html>
"""

    report = validate_generated_html(html)

    assert report.is_valid is False
    assert any("[必填]" in error for error in report.errors)
    assert any("data-anim" in warning for warning in report.warnings)
    assert any("hero slide" in warning for warning in report.warnings)
