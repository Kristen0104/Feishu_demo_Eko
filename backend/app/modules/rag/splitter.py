from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str


class TextSplitter:
    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        self._chunk_size = max(20, chunk_size)
        self._chunk_overlap = max(0, min(chunk_overlap, self._chunk_size // 2))

    def split(self, content: str) -> list[TextChunk]:
        paragraphs = [line.strip() for line in content.splitlines() if line.strip()]
        normalized = "\n".join(paragraphs).strip()
        if not normalized:
            return []
        if len(normalized) <= self._chunk_size + self._chunk_overlap:
            return [TextChunk(index=0, content=normalized)]

        units = self._semantic_units(paragraphs)
        if units:
            chunks = self._pack_units(units)
            if chunks:
                return [TextChunk(index=index, content=chunk) for index, chunk in enumerate(chunks)]

        return self._fallback_sliding_window(normalized)

    def _semantic_units(self, paragraphs: list[str]) -> list[str]:
        units: list[str] = []
        for paragraph in paragraphs:
            if len(paragraph) <= self._chunk_size:
                units.append(paragraph)
                continue
            sentences = [item.strip() for item in re.split(r"(?<=[。！？!?；;])", paragraph) if item.strip()]
            if len(sentences) <= 1:
                units.extend(
                    paragraph[index : index + self._chunk_size].strip()
                    for index in range(0, len(paragraph), self._chunk_size)
                )
            else:
                units.extend(sentences)
        return [unit for unit in units if unit]

    def _pack_units(self, units: list[str]) -> list[str]:
        raw_chunks: list[str] = []
        current = ""
        for unit in units:
            separator = "\n" if current else ""
            candidate = f"{current}{separator}{unit}" if current else unit
            if current and len(candidate) > self._chunk_size:
                raw_chunks.append(current)
                current = unit
            else:
                current = candidate
        if current:
            raw_chunks.append(current)

        min_tail_size = max(80, self._chunk_size // 3)
        if (
            len(raw_chunks) >= 2
            and len(raw_chunks[-1]) < min_tail_size
            and len(raw_chunks[-2]) + 1 + len(raw_chunks[-1]) <= self._chunk_size + self._chunk_overlap
        ):
            raw_chunks[-2] = f"{raw_chunks[-2]}\n{raw_chunks[-1]}"
            raw_chunks.pop()

        chunks: list[str] = []
        for index, chunk in enumerate(raw_chunks):
            if index == 0 or self._chunk_overlap <= 0:
                chunks.append(chunk.strip())
                continue
            overlap = self._suffix_overlap(raw_chunks[index - 1])
            chunks.append(f"{overlap}\n{chunk}".strip() if overlap else chunk.strip())
        return chunks

    def _suffix_overlap(self, content: str) -> str:
        if len(content) <= self._chunk_overlap:
            return content.strip()
        start = max(0, len(content) - self._chunk_overlap)
        boundary = max(
            content.rfind("\n", start),
            content.rfind("。", start),
            content.rfind("；", start),
        )
        if boundary > start:
            return content[boundary + 1 :].strip()
        return content[start:].strip()

    def _fallback_sliding_window(self, normalized: str) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + self._chunk_size)
            if end < len(normalized):
                boundary = max(normalized.rfind("\n", start, end), normalized.rfind("。", start, end))
                if boundary > start + self._chunk_size // 2:
                    end = boundary + 1
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(TextChunk(index=len(chunks), content=chunk))
            if end >= len(normalized):
                break
            start = max(end - self._chunk_overlap, start + 1)
        return chunks
