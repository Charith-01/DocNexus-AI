"""Deterministic page-preserving chunking for retrieval."""

import hashlib
import re

from app.schemas.retrieval import DocumentChunk


def _boundary(text: str, start: int, target: int) -> int:
    if target >= len(text):
        return len(text)
    minimum = start + max(1, (target - start) * 3 // 5)
    window = text[minimum:target]
    candidates = [window.rfind(marker) for marker in ("\n\n", ". ", "? ", "! ", " ")]
    best = max(candidates)
    return minimum + best + 1 if best >= 0 else target


def chunk_pages(
    pages: list[dict[str, int | str]],
    document_id: str,
    owner_id: str,
    filename: str,
    chunk_size: int,
    overlap: int,
) -> list[DocumentChunk]:
    """Split each page independently using character limits and soft boundaries."""

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk size or overlap")
    chunks: list[DocumentChunk] = []
    chunk_index = 0
    for page in pages:
        page_number = page.get("page_number")
        raw_text = page.get("text")
        if not isinstance(page_number, int) or page_number < 1 or not isinstance(raw_text, str):
            raise ValueError("Invalid processed page")
        text = re.sub(r"[ \t]+", " ", raw_text).strip()
        start = 0
        while start < len(text):
            end = _boundary(text, start, start + chunk_size)
            content = text[start:end].strip()
            if content:
                seed = f"{document_id}:{page_number}:{chunk_index}"
                chunk_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        owner_id=owner_id,
                        filename=filename,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        text=content,
                    )
                )
                chunk_index += 1
            if end >= len(text):
                break
            next_start = max(start + 1, end - overlap)
            while next_start < len(text) and text[next_start].isspace():
                next_start += 1
            start = next_start
    return chunks
