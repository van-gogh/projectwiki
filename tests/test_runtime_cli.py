import socket

from projectwiki.config import get_data_dir
from projectwiki.runtime import (
    RuntimePaths,
    choose_port,
    default_runtime_paths,
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


def test_choose_port_falls_back_when_preferred_port_is_occupied():
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        occupied_port = int(sock.getsockname()[1])

        port = choose_port(host, preferred=occupied_port)

    assert isinstance(port, int)
    assert port > 0
    assert port != occupied_port


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
