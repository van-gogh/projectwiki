from __future__ import annotations

from datetime import datetime, timezone
from errno import EADDRINUSE
import json
import os
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .config import get_data_dir


class PortInUseError(OSError):
    def __init__(self, host: str, port: int):
        super().__init__(EADDRINUSE, f"Port {host}:{port} is already in use")
        self.host = host
        self.port = port


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    command: str = "unknown"


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
        return self.log_dir / "whywiki.log"


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
            raise PortInUseError(host, preferred) from exc
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


def probe_whywiki_server(state: dict[str, Any], timeout: float = 0.5) -> bool:
    try:
        host = str(state["host"])
        port = int(state["port"])
    except (KeyError, TypeError, ValueError):
        return False

    try:
        with urlopen(f"http://{host}:{port}/", timeout=timeout) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
    except (HTTPError, OSError, URLError, TimeoutError, ValueError):
        return False
    return "WhyWiki" in body


def find_listening_process(host: str, port: int) -> ProcessInfo | None:
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-F", "pc"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None

    pid: int | None = None
    command = ""
    for line in result.stdout.splitlines():
        if line.startswith("p"):
            try:
                pid = int(line[1:])
            except ValueError:
                pid = None
        elif line.startswith("c") and line[1:]:
            command = line[1:]
        if pid is not None and command:
            return ProcessInfo(pid=pid, command=command)
    if pid is not None:
        return ProcessInfo(pid=pid)
    return None


def stop_process(pid: int, timeout: float = 5.0) -> None:
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)


def read_active_runtime_state(
    paths: RuntimePaths,
    probe: Callable[[dict[str, Any]], bool] = probe_whywiki_server,
) -> dict[str, Any] | None:
    state = read_runtime_state(paths)
    if state is None:
        return None
    if probe(state):
        return state
    clear_runtime_state(paths)
    return None


def read_log_tail(paths: RuntimePaths, lines: int = 80) -> str:
    if not paths.log_path.exists():
        return "No WhyWiki log file found.\n"
    content = paths.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:]) + ("\n" if content else "")
