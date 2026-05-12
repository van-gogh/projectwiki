from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..models import ParsedBlock


class Parser(Protocol):
    def parse(self, path: Path) -> list[ParsedBlock]:
        ...
