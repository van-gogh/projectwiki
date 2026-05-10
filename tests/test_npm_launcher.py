import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_package_json_exposes_projectwiki_bin():
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["name"] == "projectwiki"
    assert package["bin"]["projectwiki"] == "npm/projectwiki.js"


def test_node_launcher_delegates_to_python_cli():
    script = (ROOT / "npm" / "projectwiki.js").read_text(encoding="utf-8")

    assert "python" in script
    assert "projectwiki.cli" in script
    assert "spawn" in script


def test_node_launcher_runs_python_cli_from_outside_repo(tmp_path):
    result = subprocess.run(
        ["node", str(ROOT / "npm" / "projectwiki.js"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
    assert "projectwiki" in result.stdout


def test_node_launcher_delegates_default_startup_and_sets_data_dir():
    script = (ROOT / "npm" / "projectwiki.js").read_text(encoding="utf-8")

    assert '["serve", "--host", "127.0.0.1", "--port", "8765"]' in script
    assert "ProjectWiki is running locally." not in script
    assert "Open: http://127.0.0.1:8765" not in script
    assert "Logs: projectwiki log" not in script
    assert "PROJECTWIKI_DATA_DIR" in script
    assert ".projectwiki" in script
    assert "homedir" in script


def test_node_launcher_child_exit_helper_preserves_signals():
    node_code = f"""
const launcher = require({json.dumps(str(ROOT / "npm" / "projectwiki.js"))});
let exitCode = null;
let killed = null;
launcher.exitFromChild(null, "SIGTERM", {{
  pid: 12345,
  kill: (pid, signal) => {{ killed = [pid, signal]; }},
  exit: (code) => {{ exitCode = code; }}
}});
if (!killed || killed[0] !== 12345 || killed[1] !== "SIGTERM" || exitCode !== null) {{
  process.exit(1);
}}
launcher.exitFromChild(null, "SIGTERM", {{
  pid: 12345,
  kill: () => {{ throw new Error("cannot signal"); }},
  exit: (code) => {{ exitCode = code; }}
}});
if (exitCode !== 128) {{
  process.exit(2);
}}
launcher.exitFromChild(null, null, {{
  pid: 12345,
  kill: () => {{}},
  exit: (code) => {{ exitCode = code; }}
}});
if (exitCode !== 1) {{
  process.exit(3);
}}
"""
    result = subprocess.run(
        ["node", "-e", node_code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr


def test_npmignore_excludes_generated_python_artifacts():
    npmignore = (ROOT / ".npmignore").read_text(encoding="utf-8")

    assert "__pycache__/" in npmignore
    assert "*.pyc" in npmignore
    assert ".pytest_cache/" in npmignore
    assert ".worktrees/" in npmignore
    assert ".projectwiki/" in npmignore


def test_package_files_exclude_python_bytecode_from_allowlist():
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert "!projectwiki/**/__pycache__/" in package["files"]
    assert "!projectwiki/**/*.pyc" in package["files"]


def test_npm_pack_dry_run_excludes_generated_python_artifacts(tmp_path):
    result = subprocess.run(
        ["npm", "--cache", str(tmp_path / "npm-cache"), "pack", "--dry-run", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    [package] = json.loads(result.stdout)
    paths = [entry["path"] for entry in package["files"]]

    assert not any("__pycache__" in path for path in paths)
    assert not any(path.endswith(".pyc") for path in paths)
