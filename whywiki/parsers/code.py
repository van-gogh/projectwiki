from __future__ import annotations

import ast
import re
from pathlib import Path

from ..models import ParsedBlock

ENDPOINT_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_/{}/.:-]+)", re.IGNORECASE)
DECORATOR_ENDPOINT_RE = re.compile(r"@(?:app|router)\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]")
GENERIC_FUNC_RE = re.compile(r"\b(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*(?:=>|\{)?")


def parse_code(path: Path) -> list[ParsedBlock]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    blocks: list[ParsedBlock] = []

    if path.suffix.lower() == ".py":
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    blocks.append(
                        ParsedBlock(
                            "code_symbol",
                            f"Python function `{node.name}` defined in {path.name}",
                            {"line": getattr(node, "lineno", None), "symbol": node.name},
                            {"kind": "function"},
                        )
                    )
                elif isinstance(node, ast.ClassDef):
                    blocks.append(
                        ParsedBlock(
                            "code_symbol",
                            f"Python class `{node.name}` defined in {path.name}",
                            {"line": getattr(node, "lineno", None), "symbol": node.name},
                            {"kind": "class"},
                        )
                    )
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = []
                    if isinstance(node, ast.Import):
                        names = [a.name for a in node.names]
                    elif node.module:
                        names = [node.module]
                    if names:
                        blocks.append(
                            ParsedBlock(
                                "code_import",
                                f"Python import: {', '.join(names)}",
                                {"line": getattr(node, "lineno", None)},
                                {"modules": names},
                            )
                        )
        except SyntaxError:
            pass

    for match in DECORATOR_ENDPOINT_RE.finditer(text):
        method = match.group(1).upper()
        route = match.group(2)
        blocks.append(
            ParsedBlock(
                "code_endpoint",
                f"Code defines API endpoint {method} {route}",
                {"method": method, "path": route},
                {"parser": "regex"},
            )
        )

    for match in ENDPOINT_RE.finditer(text):
        method = match.group(1).upper()
        route = match.group(2)
        blocks.append(
            ParsedBlock(
                "mentioned_endpoint",
                f"Text mentions API endpoint {method} {route}",
                {"method": method, "path": route},
                {"parser": "regex"},
            )
        )

    if not blocks:
        preview = "\n".join(text.splitlines()[:80]).strip()
        if preview:
            blocks.append(ParsedBlock("code_file", preview, {"file": path.name}, {"parser": "fallback"}))
    return blocks
