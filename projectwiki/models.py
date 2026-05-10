from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedBlock:
    block_type: str
    text: str
    location: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidencePointer:
    source_id: str
    block_id: str | None = None
    path: str | None = None
    location: dict[str, Any] = field(default_factory=dict)
