from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class HtmlValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_generated_html(html: str) -> HtmlValidationReport:
    report = HtmlValidationReport()

    required_markers = {
        "<!DOCTYPE html>": "Missing required DOCTYPE declaration.",
        "<html": "Missing required <html> root element.",
        "<title>": "Missing required <title> element.",
        'id="deck"': 'Missing required id="deck" container.',
        'class="slide': 'Missing required class="slide..." section.',
    }
    for marker, message in required_markers.items():
        if marker not in html:
            report.errors.append(message)

    if "[必填]" in html:
        report.errors.append('Generated HTML still contains unresolved "[必填]" placeholders.')

    if re.search(r'class="[^"\n<>]*>', html):
        report.errors.append('Generated HTML contains an unclosed class attribute before ">".')

    if "data-anim" not in html:
        report.warnings.append('Generated HTML does not include any "data-anim" markers.')

    if 'class="slide hero ' not in html and 'class="slide hero"' not in html:
        report.warnings.append("Generated HTML does not include a hero slide.")

    return report
