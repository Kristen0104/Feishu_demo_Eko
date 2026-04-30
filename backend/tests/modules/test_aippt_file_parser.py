from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.aippt.file_parser import FileParser


def test_file_parser_reads_markdown_and_text_files(tmp_path) -> None:
    md_file = tmp_path / "brief.md"
    txt_file = tmp_path / "brief.txt"
    md_file.write_text("# Hello\n\nWorld", encoding="utf-8")
    txt_file.write_text("Plain text", encoding="utf-8")

    parser = FileParser(vendor_root=tmp_path / "vendor")

    assert "# Hello" in parser.parse_input_file(md_file)
    assert parser.parse_input_file(txt_file) == "Plain text"


def test_file_parser_rejects_unsupported_suffix(tmp_path) -> None:
    parser = FileParser(vendor_root=tmp_path / "vendor")
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        parser.parse_input_file(bad)
