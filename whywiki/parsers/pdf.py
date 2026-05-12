from __future__ import annotations

from pathlib import Path

from ..models import ParsedBlock


def parse_pdf(path: Path) -> list[ParsedBlock]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to parse .pdf files") from exc

    reader = PdfReader(str(path))
    blocks: list[ParsedBlock] = []
    for page_idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            blocks.append(ParsedBlock("pdf_page", text, {"page": page_idx}, {}))
    return blocks
