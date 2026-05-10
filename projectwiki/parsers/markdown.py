from __future__ import annotations

import re
from pathlib import Path

from ..models import ParsedBlock
from .plaintext import parse_plaintext

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def parse_markdown(path: Path) -> list[ParsedBlock]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return parse_plaintext(path)

    blocks: list[ParsedBlock] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        level = len(match.group(1))
        heading = match.group(2).strip()
        blocks.append(
            ParsedBlock(
                "markdown_section",
                section,
                {"heading": heading, "level": level, "section_index": idx + 1},
                {"parser": "markdown"},
            )
        )
    return blocks
