from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import get_data_dir
from ..utils import new_id
from .local_files import LocalFilesConnector


class GitRepoConnector:
    """A tiny Git connector.

    First-board behavior:
    - If `repo` is a local path, walk it like a local directory.
    - If `repo` looks remote, clone it into the data directory and walk the clone.
    """

    def __init__(self, repo: str | Path):
        self.repo = str(repo)
        self.local_path = self._prepare_repo()

    def _prepare_repo(self) -> Path:
        maybe_path = Path(self.repo).expanduser()
        if maybe_path.exists():
            return maybe_path.resolve()
        target = get_data_dir() / "repos" / new_id("repo")
        subprocess.run(["git", "clone", "--depth", "1", self.repo, str(target)], check=True)
        return target

    def list_files(self) -> list[Path]:
        return LocalFilesConnector(self.local_path).list_files()
