from __future__ import annotations

import csv
from pathlib import Path

from ..models import ParsedBlock


def parse_csv(path: Path) -> list[ParsedBlock]:
    blocks: list[ParsedBlock] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return []
    headers = [h.strip() or f"col_{i+1}" for i, h in enumerate(rows[0])]
    for row_idx, row in enumerate(rows[1:], start=2):
        values = {headers[i] if i < len(headers) else f"col_{i+1}": v for i, v in enumerate(row)}
        text = "; ".join(f"{k}: {v}" for k, v in values.items() if str(v).strip())
        if text:
            blocks.append(ParsedBlock("table_row", text, {"row": row_idx}, {"headers": headers, "values": values}))
    return blocks
