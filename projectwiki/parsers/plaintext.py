from __future__ import annotations

from pathlib import Path

from ..models import ParsedBlock


def parse_plaintext(path: Path, chunk_size: int = 1600) -> list[ParsedBlock]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    blocks: list[ParsedBlock] = []
    buffer = ""
    chunk_no = 1
    for para in paragraphs or [text]:
        if len(buffer) + len(para) + 2 > chunk_size and buffer:
            blocks.append(ParsedBlock("text", buffer.strip(), {"chunk": chunk_no}, {}))
            chunk_no += 1
            buffer = ""
        buffer += para + "\n\n"
    if buffer.strip():
        blocks.append(ParsedBlock("text", buffer.strip(), {"chunk": chunk_no}, {}))
    return blocks
