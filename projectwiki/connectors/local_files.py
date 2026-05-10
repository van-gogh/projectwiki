from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".rst",
    ".csv", ".xlsx", ".docx", ".pdf",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rs", ".cpp", ".c", ".h",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".sh", ".sql"
}

IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".projectwiki"}


class LocalFilesConnector:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def list_files(self) -> list[Path]:
        if self.root.is_file():
            return [self.root] if self.root.suffix.lower() in SUPPORTED_EXTENSIONS else []
        files: list[Path] = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORE_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(path)
        return sorted(files)
