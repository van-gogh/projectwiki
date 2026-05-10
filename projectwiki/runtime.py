from __future__ import annotations

from datetime import datetime, timezone
from errno import EADDRINUSE
import json
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import get_data_dir


@dataclass(frozen=True)
class RuntimePaths:
    data_dir: Path

    @property
    def run_dir(self) -> Path:
        return self.data_dir / "run"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def state_path(self) -> Path:
        return self.run_dir / "server.json"

    @property
    def log_path(self) -> Path:
        return self.log_dir / "projectwiki.log"


def default_runtime_paths() -> RuntimePaths:
    return RuntimePaths(get_data_dir())


def ensure_runtime_dirs(paths: RuntimePaths) -> None:
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    paths.log_dir.mkdir(parents=True, exist_ok=True)


def choose_port(host: str = "127.0.0.1", preferred: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, preferred))
        except OSError as exc:
            if exc.errno != EADDRINUSE:
                raise
            sock.bind((host, 0))
        return int(sock.getsockname()[1])


def write_runtime_state(paths: RuntimePaths, host: str, port: int, pid: int) -> None:
    ensure_runtime_dirs(paths)
    payload = {
        "host": host,
        "port": port,
        "pid": pid,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    paths.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clear_runtime_state(paths: RuntimePaths) -> None:
    try:
        paths.state_path.unlink()
    except FileNotFoundError:
        return


def append_runtime_log(paths: RuntimePaths, line: str) -> None:
    ensure_runtime_dirs(paths)
    with paths.log_path.open("a", encoding="utf-8") as log:
        log.write(line.rstrip("\n") + "\n")


def read_runtime_state(paths: RuntimePaths) -> dict[str, Any] | None:
    try:
        return json.loads(paths.state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def read_log_tail(paths: RuntimePaths, lines: int = 80) -> str:
    if not paths.log_path.exists():
        return "No ProjectWiki log file found.\n"
    content = paths.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:]) + ("\n" if content else "")
