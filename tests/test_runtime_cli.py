import socket
import sys
import types

from projectwiki.config import get_data_dir
from projectwiki.runtime import (
    PortInUseError,
    RuntimePaths,
    append_runtime_log,
    choose_port,
    clear_runtime_state,
    default_runtime_paths,
    read_active_runtime_state,
    read_log_tail,
    read_runtime_state,
    write_runtime_state,
)
from projectwiki.cli import main


def test_runtime_state_round_trip(tmp_path):
    paths = RuntimePaths(tmp_path)
    write_runtime_state(paths, host="127.0.0.1", port=8765, pid=1234)

    state = read_runtime_state(paths)

    assert state["host"] == "127.0.0.1"
    assert state["port"] == 8765
    assert state["pid"] == 1234
    assert "started_at" in state


def test_clear_runtime_state_removes_state_file(tmp_path):
    paths = RuntimePaths(tmp_path)
    write_runtime_state(paths, host="127.0.0.1", port=8765, pid=1234)

    clear_runtime_state(paths)

    assert read_runtime_state(paths) is None


def test_append_runtime_log_creates_log_file(tmp_path):
    paths = RuntimePaths(tmp_path)

    append_runtime_log(paths, "ProjectWiki started")

    assert "ProjectWiki started\n" in paths.log_path.read_text(encoding="utf-8")


def test_default_runtime_paths_match_configured_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))

    assert default_runtime_paths().data_dir == get_data_dir()


def test_default_runtime_paths_match_config_default_in_current_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("PROJECTWIKI_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    assert default_runtime_paths().data_dir == get_data_dir()


def test_read_runtime_state_returns_none_for_corrupt_json(tmp_path):
    paths = RuntimePaths(tmp_path)
    paths.state_path.parent.mkdir(parents=True, exist_ok=True)
    paths.state_path.write_text("{not json", encoding="utf-8")

    assert read_runtime_state(paths) is None


def test_read_runtime_state_returns_none_for_invalid_utf8(tmp_path):
    paths = RuntimePaths(tmp_path)
    paths.state_path.parent.mkdir(parents=True, exist_ok=True)
    paths.state_path.write_bytes(b"\xff\xfe\xfa")

    assert read_runtime_state(paths) is None


def test_log_tail_returns_recent_lines(tmp_path):
    paths = RuntimePaths(tmp_path)
    paths.log_path.parent.mkdir(parents=True, exist_ok=True)
    paths.log_path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert read_log_tail(paths, lines=2) == "two\nthree\n"


def test_choose_port_returns_requested_free_port():
    port = choose_port("127.0.0.1", preferred=0)

    assert isinstance(port, int)
    assert port > 0


def test_choose_port_refuses_occupied_preferred_port():
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        occupied_port = int(sock.getsockname()[1])

        try:
            choose_port(host, preferred=occupied_port)
        except PortInUseError as exc:
            assert exc.host == host
            assert exc.port == occupied_port
        else:
            raise AssertionError("occupied preferred port should not fall back")


def test_active_runtime_state_returns_none_and_clears_stale_state(tmp_path):
    paths = RuntimePaths(tmp_path)
    write_runtime_state(paths, host="127.0.0.1", port=8765, pid=1234)

    state = read_active_runtime_state(paths, probe=lambda candidate: False)

    assert state is None
    assert read_runtime_state(paths) is None


def test_status_reports_not_running_without_state(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))

    assert main(["status"]) == 0

    assert '"running": false' in capsys.readouterr().out


def test_log_command_prints_recent_lines(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))
    paths = RuntimePaths(tmp_path)
    paths.log_path.parent.mkdir(parents=True, exist_ok=True)
    paths.log_path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert main(["log", "--lines", "2"]) == 0

    assert capsys.readouterr().out == "two\nthree\n"


def test_serve_writes_actual_runtime_state_and_log(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("projectwiki.cli.choose_port", lambda host, preferred: preferred)
    calls = []

    def record_run(app, host, port, reload):
        state = read_runtime_state(RuntimePaths(tmp_path))
        assert state is not None
        assert state["host"] == "127.0.0.1"
        assert state["port"] == 8765
        calls.append({"app": app, "host": host, "port": port, "reload": reload})

    fake_uvicorn = types.SimpleNamespace(
        run=record_run
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    assert main(["serve", "--host", "127.0.0.1", "--port", "8765"]) == 0

    assert calls == [
        {
            "app": "projectwiki.app:app",
            "host": "127.0.0.1",
            "port": 8765,
            "reload": False,
        }
    ]
    assert read_runtime_state(RuntimePaths(tmp_path)) is None
    output = capsys.readouterr().out
    assert "Open: http://127.0.0.1:8765" in output
    assert "Logs: projectwiki log" in output
    log = RuntimePaths(tmp_path).log_path.read_text(encoding="utf-8")
    assert "Starting ProjectWiki on http://127.0.0.1:8765" in log
    assert "ProjectWiki server stopped." in log


def test_serve_reuses_active_runtime_state_without_starting_second_server(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))
    write_runtime_state(RuntimePaths(tmp_path), host="127.0.0.1", port=8765, pid=1234)
    monkeypatch.setattr("projectwiki.cli.read_active_runtime_state", lambda paths: {
        "host": "127.0.0.1",
        "port": 8765,
        "pid": 1234,
    })

    def unexpected_run(*args, **kwargs):
        raise AssertionError("serve should not start a second server")

    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=unexpected_run))

    assert main(["serve", "--host", "127.0.0.1", "--port", "8765"]) == 0

    output = capsys.readouterr().out
    assert "ProjectWiki is already running locally." in output
    assert "Open: http://127.0.0.1:8765" in output
    assert "Logs: projectwiki log" in output


def test_serve_refuses_occupied_port_without_fallback(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("projectwiki.cli.read_active_runtime_state", lambda paths: None)
    monkeypatch.setattr(
        "projectwiki.cli.choose_port",
        lambda host, preferred: (_ for _ in ()).throw(PortInUseError(host, preferred)),
    )

    assert main(["serve", "--host", "127.0.0.1", "--port", "8765"]) == 2

    captured = capsys.readouterr()
    assert "Port 127.0.0.1:8765 is already in use." in captured.err
    assert "ProjectWiki will not choose another port automatically." in captured.err
    assert "Open:" not in captured.out


def test_serve_clears_runtime_state_when_uvicorn_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("projectwiki.cli.choose_port", lambda host, preferred: preferred)

    def raise_from_run(app, host, port, reload):
        assert port == 8765
        raise RuntimeError("server failed")

    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=raise_from_run))

    try:
        main(["serve", "--host", "127.0.0.1", "--port", "8765"])
    except RuntimeError as exc:
        assert str(exc) == "server failed"
    else:
        raise AssertionError("uvicorn failure was not propagated")

    assert read_runtime_state(RuntimePaths(tmp_path)) is None
    assert "ProjectWiki server stopped." in RuntimePaths(tmp_path).log_path.read_text(encoding="utf-8")


def test_doctor_reports_runtime_files(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))

    assert main(["doctor"]) == 0

    output = capsys.readouterr().out
    assert str(tmp_path.resolve()) in output
    assert '"state_file_exists": false' in output
    assert '"log_file_exists": false' in output


def test_open_prints_runtime_url(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path))
    write_runtime_state(RuntimePaths(tmp_path), host="127.0.0.1", port=8765, pid=1234)

    assert main(["open"]) == 0

    assert capsys.readouterr().out == "http://127.0.0.1:8765\n"


def test_stop_reports_not_active(capsys):
    assert main(["stop"]) == 0

    assert capsys.readouterr().out == "Stop is not active yet. Use Ctrl+C for foreground serve sessions.\n"
