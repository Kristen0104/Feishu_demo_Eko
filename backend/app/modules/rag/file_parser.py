from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import docx2txt
from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedRagUpload:
    filename: str
    file_type: str
    text: str


def parse_rag_upload(filename: str, content: bytes) -> ParsedRagUpload:
    suffix = Path(filename).suffix.lower()
    if suffix in {".md", ".markdown"}:
        return ParsedRagUpload(filename=filename, file_type="markdown", text=_decode_text(content))
    if suffix in {".txt", ".csv", ".json", ".log"}:
        return ParsedRagUpload(filename=filename, file_type=suffix.lstrip("."), text=_decode_text(content))
    if suffix == ".pdf":
        return ParsedRagUpload(filename=filename, file_type="pdf", text=_parse_pdf(content))
    if suffix == ".docx":
        return ParsedRagUpload(filename=filename, file_type="docx", text=_parse_docx(content))
    raise ValueError("Unsupported RAG file type. Upload md, txt, csv, json, log, pdf, or docx.")


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return content.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore").strip()


def _parse_pdf(content: bytes) -> str:
    with NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(content)
        tmp.flush()
        reader = PdfReader(tmp.name)
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        text = "\n\n".join(page for page in pages if page).strip()
        if text:
            return text
        title = reader.metadata.title if reader.metadata and reader.metadata.title else ""
        return title.strip() or "PDF 文件已解析，但未提取到可读文本。"


def _parse_docx(content: bytes) -> str:
    with NamedTemporaryFile(suffix=".docx") as tmp:
        tmp.write(content)
        tmp.flush()
        return (docx2txt.process(tmp.name) or "").strip()
