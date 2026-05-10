from __future__ import annotations

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Return the ProjectWiki data directory and create it if missing."""
    root = Path(os.getenv("PROJECTWIKI_DATA_DIR", ".projectwiki")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)
    (root / "repos").mkdir(parents=True, exist_ok=True)
    return root


def get_db_path() -> Path:
    return get_data_dir() / "projectwiki.db"


def get_project_dir(project_id: str) -> Path:
    path = get_data_dir() / "projects" / project_id
    path.mkdir(parents=True, exist_ok=True)
    (path / "wiki").mkdir(parents=True, exist_ok=True)
    return path
