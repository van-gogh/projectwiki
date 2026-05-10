# First Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ProjectWiki first board: npm-first local launch, logs, stronger project-memory data, deterministic ingestion/facts/conflicts, evidence-backed wiki/handover/ask, and a bilingual dashboard UI.

**Architecture:** Keep the existing FastAPI + SQLite + static Web architecture, then add focused modules around it. The Python CLI becomes the reliable local service layer; an npm launcher wraps it. The Web UI calls local JSON APIs and renders bilingual dashboard chrome while preserving source evidence in its original language.

**Tech Stack:** Python 3.10+, FastAPI, SQLite, pytest, vanilla HTML/CSS/JS for the first-board dashboard, Node.js for the npm launcher.

---

## Scope Note

This is a broad first-board plan, so it is split into independently shippable tasks. Each task should be implemented with tests, verified, committed, and reviewed before moving to the next one.

## File Structure

Create or modify these files:

- `projectwiki/db.py`: schema migrations and indexes.
- `projectwiki/runtime.py`: local runtime metadata, logs, status, port selection.
- `projectwiki/cli.py`: `projectwiki`, `open`, `status`, `log`, `stop`, `doctor`, and current developer commands.
- `projectwiki/app.py`: Web API endpoints for dashboard, sources, blocks, facts, logs, and conflict status.
- `projectwiki/services/ingest.py`: source update behavior and parse diagnostics.
- `projectwiki/services/fact_extractor.py`: fact status, validity status, confidence handling.
- `projectwiki/services/conflict_detector.py`: deployment-model mismatch and stronger evidence.
- `projectwiki/services/wiki_engine.py`: evidence rendering and uncertainty labels.
- `projectwiki/services/handover.py`: evidence-first handover sections.
- `projectwiki/services/ask.py`: structured evidence and insufficient-evidence behavior.
- `projectwiki/static/index.html`: dashboard shell.
- `projectwiki/static/styles.css`: dashboard visual system.
- `projectwiki/static/app.js`: API client and dashboard behavior.
- `projectwiki/static/i18n.js`: Chinese/English UI strings and language selection.
- `package.json`: npm package entry and bin command.
- `npm/projectwiki.js`: Node launcher that calls the Python runtime.
- `tests/test_schema_migration.py`: schema and backward-compatibility tests.
- `tests/test_runtime_cli.py`: runtime/log/status behavior tests.
- `tests/test_api_surface.py`: API visibility tests.
- `tests/test_conflict_detector.py`: conflict rule tests.
- `tests/test_web_assets.py`: Web asset and i18n tests.
- `README.md`: product startup and demo path.

---

### Task 1: Schema Migration And Evidence Fields

**Files:**
- Modify: `projectwiki/db.py`
- Test: `tests/test_schema_migration.py`

- [ ] **Step 1: Write failing migration tests**

Create `tests/test_schema_migration.py`:

```python
import sqlite3

from projectwiki.db import init_db


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_init_db_adds_schema_version_and_review_fields(tmp_path):
    db_path = tmp_path / "projectwiki.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    init_db(conn)

    version = conn.execute("SELECT version FROM schema_version").fetchone()
    assert version["version"] >= 1
    assert {"status"}.issubset(columns(conn, "projects"))
    assert {"version_hint"}.issubset(columns(conn, "sources"))
    assert {"validity_status"}.issubset(columns(conn, "facts"))


def test_init_db_is_idempotent(tmp_path):
    db_path = tmp_path / "projectwiki.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    init_db(conn)
    init_db(conn)

    assert "validity_status" in columns(conn, "facts")
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
python -m pytest tests/test_schema_migration.py -q
```

Expected: FAIL because `schema_version`, `projects.status`, `sources.version_hint`, or `facts.validity_status` does not exist.

- [ ] **Step 3: Implement lightweight migrations**

Modify `projectwiki/db.py` by adding helpers:

```python
def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in rows}


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column not in table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def apply_migrations(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version(version) VALUES (0)")

    ensure_column(conn, "projects", "status", "TEXT DEFAULT 'active'")
    ensure_column(conn, "sources", "version_hint", "TEXT DEFAULT ''")
    ensure_column(conn, "facts", "validity_status", "TEXT DEFAULT 'unknown'")

    conn.execute("UPDATE schema_version SET version = 1")
```

Call `apply_migrations(conn)` after the base schema is created and before `conn.commit()`.

- [ ] **Step 4: Run schema tests**

Run:

```bash
python -m pytest tests/test_schema_migration.py -q
```

Expected: PASS.

- [ ] **Step 5: Run full verification**

Run:

```bash
python -m compileall projectwiki
python -m pytest -q
```

Expected: both commands pass.

- [ ] **Step 6: Commit**

```bash
git add projectwiki/db.py tests/test_schema_migration.py
git commit -m "feat: add schema migrations"
```

---

### Task 2: Runtime Status, Logs, And Python CLI Launcher

**Files:**
- Create: `projectwiki/runtime.py`
- Modify: `projectwiki/cli.py`
- Test: `tests/test_runtime_cli.py`

- [ ] **Step 1: Write runtime tests**

Create `tests/test_runtime_cli.py`:

```python
from projectwiki.runtime import (
    RuntimePaths,
    choose_port,
    read_log_tail,
    write_runtime_state,
    read_runtime_state,
)


def test_runtime_state_round_trip(tmp_path):
    paths = RuntimePaths(tmp_path)
    write_runtime_state(paths, host="127.0.0.1", port=8765, pid=1234)

    state = read_runtime_state(paths)

    assert state["host"] == "127.0.0.1"
    assert state["port"] == 8765
    assert state["pid"] == 1234


def test_log_tail_returns_recent_lines(tmp_path):
    paths = RuntimePaths(tmp_path)
    paths.log_path.parent.mkdir(parents=True, exist_ok=True)
    paths.log_path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert read_log_tail(paths, lines=2) == "two\nthree\n"


def test_choose_port_returns_requested_free_port():
    port = choose_port("127.0.0.1", preferred=0)

    assert isinstance(port, int)
    assert port > 0
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python -m pytest tests/test_runtime_cli.py -q
```

Expected: FAIL because `projectwiki.runtime` does not exist.

- [ ] **Step 3: Implement runtime helpers**

Create `projectwiki/runtime.py`:

```python
from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    root = Path(os.getenv("PROJECTWIKI_DATA_DIR", "~/.projectwiki")).expanduser().resolve()
    return RuntimePaths(root)


def choose_port(host: str = "127.0.0.1", preferred: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, preferred))
        return int(sock.getsockname()[1])


def write_runtime_state(paths: RuntimePaths, host: str, port: int, pid: int) -> None:
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    payload = {"host": host, "port": port, "pid": pid}
    paths.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_runtime_state(paths: RuntimePaths) -> dict[str, Any] | None:
    if not paths.state_path.exists():
        return None
    return json.loads(paths.state_path.read_text(encoding="utf-8"))


def read_log_tail(paths: RuntimePaths, lines: int = 80) -> str:
    if not paths.log_path.exists():
        return "No ProjectWiki log file found.\n"
    content = paths.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:]) + ("\n" if content else "")
```

- [ ] **Step 4: Extend CLI command surface**

Modify `projectwiki/cli.py`:

```python
from .runtime import default_runtime_paths, read_log_tail, read_runtime_state
```

Add subcommands:

```python
sub.add_parser("open")
sub.add_parser("status")

p_log = sub.add_parser("log")
p_log.add_argument("--lines", type=int, default=80)

sub.add_parser("doctor")
sub.add_parser("stop")
```

Add handlers:

```python
    if args.command == "status":
        state = read_runtime_state(default_runtime_paths())
        print(json.dumps(state or {"running": False}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "log":
        print(read_log_tail(default_runtime_paths(), args.lines), end="")
        return 0

    if args.command == "doctor":
        paths = default_runtime_paths()
        print(json.dumps({
            "data_dir": str(paths.data_dir),
            "state_file_exists": paths.state_path.exists(),
            "log_file_exists": paths.log_path.exists(),
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "open":
        state = read_runtime_state(default_runtime_paths()) or {}
        url = f"http://{state.get('host', '127.0.0.1')}:{state.get('port', 8765)}"
        print(url)
        return 0

    if args.command == "stop":
        print("Stop is not active yet. Use Ctrl+C for foreground serve sessions.")
        return 0
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/test_runtime_cli.py -q
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add projectwiki/runtime.py projectwiki/cli.py tests/test_runtime_cli.py
git commit -m "feat: add runtime status and logs"
```

---

### Task 3: Npm Launcher Package

**Files:**
- Create: `package.json`
- Create: `npm/projectwiki.js`
- Test: `tests/test_npm_launcher.py`

- [ ] **Step 1: Write launcher file tests**

Create `tests/test_npm_launcher.py`:

```python
import json
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
```

- [ ] **Step 2: Run failing launcher tests**

Run:

```bash
python -m pytest tests/test_npm_launcher.py -q
```

Expected: FAIL because `package.json` and `npm/projectwiki.js` do not exist.

- [ ] **Step 3: Add package metadata**

Create `package.json`:

```json
{
  "name": "projectwiki",
  "version": "0.1.0",
  "description": "Local-first project memory and AI-maintained wiki for messy software projects.",
  "license": "MIT",
  "type": "commonjs",
  "bin": {
    "projectwiki": "npm/projectwiki.js"
  },
  "files": [
    "npm",
    "projectwiki",
    "pyproject.toml",
    "README.md",
    "LICENSE"
  ],
  "engines": {
    "node": ">=18"
  }
}
```

- [ ] **Step 4: Add Node launcher**

Create `npm/projectwiki.js`:

```javascript
#!/usr/bin/env node

const { spawn } = require("node:child_process");

const args = process.argv.slice(2);
const passthrough = args.length === 0 ? ["serve", "--host", "127.0.0.1", "--port", "8765"] : args;
const candidates = process.platform === "win32"
  ? ["python.exe", "python3.exe"]
  : ["python3", "python"];

function run(index) {
  if (index >= candidates.length) {
    console.error("ProjectWiki could not find Python. Install Python 3.10+ and run again.");
    process.exit(1);
  }

  const child = spawn(candidates[index], ["-m", "projectwiki.cli"].concat(passthrough), {
    stdio: "inherit"
  });

  child.on("error", () => run(index + 1));
  child.on("exit", (code) => process.exit(code || 0));
}

run(0);
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/test_npm_launcher.py -q
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add package.json npm/projectwiki.js tests/test_npm_launcher.py
git commit -m "feat: add npm launcher"
```

---

### Task 4: Dashboard API Surface

**Files:**
- Modify: `projectwiki/app.py`
- Test: `tests/test_api_surface.py`

- [ ] **Step 1: Write API surface tests**

Create `tests/test_api_surface.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from projectwiki.app import app
from projectwiki.services.ingest import ingest_path
from projectwiki.services.wiki_engine import build_project
from projectwiki.services.workspace import create_project


def test_dashboard_api_lists_sources_facts_and_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)
    project = create_project("Demo")
    root = Path(__file__).resolve().parents[1] / "examples" / "demo-project"
    ingest_path(project["id"], root)
    build_project(project["id"])

    sources = client.get(f"/api/projects/{project['id']}/sources")
    facts = client.get(f"/api/projects/{project['id']}/facts")

    assert sources.status_code == 200
    assert facts.status_code == 200
    assert sources.json()
    assert facts.json()

    source_id = sources.json()[0]["id"]
    blocks = client.get(f"/api/projects/{project['id']}/sources/{source_id}/blocks")
    assert blocks.status_code == 200
    assert blocks.json()
```

- [ ] **Step 2: Run failing API test**

Run:

```bash
python -m pytest tests/test_api_surface.py -q
```

Expected: FAIL because source, block, and fact endpoints do not exist.

- [ ] **Step 3: Add endpoints**

Modify `projectwiki/app.py`:

```python
@app.get("/api/projects/{project_id}/sources")
def api_list_sources(project_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sources WHERE project_id = ? ORDER BY path",
            (project_id,),
        ).fetchall()
        return rows_to_dicts(rows)


@app.get("/api/projects/{project_id}/sources/{source_id}/blocks")
def api_list_source_blocks(project_id: str, source_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM blocks
            WHERE project_id = ? AND source_id = ?
            ORDER BY id
            """,
            (project_id, source_id),
        ).fetchall()
        return rows_to_dicts(rows)


@app.get("/api/projects/{project_id}/facts")
def api_list_facts(project_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM facts WHERE project_id = ? ORDER BY fact_type, confidence DESC",
            (project_id,),
        ).fetchall()
        return rows_to_dicts(rows)
```

- [ ] **Step 4: Add conflict status endpoint**

Extend `projectwiki/app.py`:

```python
class ConflictStatusRequest(BaseModel):
    status: str


@app.patch("/api/projects/{project_id}/conflicts/{conflict_id}")
def api_update_conflict(project_id: str, conflict_id: str, req: ConflictStatusRequest) -> dict:
    if req.status not in {"open", "resolved", "ignored"}:
        raise HTTPException(status_code=400, detail="Invalid conflict status")
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM conflicts WHERE project_id = ? AND id = ?",
            (project_id, conflict_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Conflict not found")
        conn.execute(
            "UPDATE conflicts SET status = ? WHERE project_id = ? AND id = ?",
            (req.status, project_id, conflict_id),
        )
        conn.commit()
        return {"id": conflict_id, "status": req.status}
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/test_api_surface.py -q
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add projectwiki/app.py tests/test_api_surface.py
git commit -m "feat: expose dashboard APIs"
```

---

### Task 5: Conflict Detection Enhancements

**Files:**
- Modify: `projectwiki/services/conflict_detector.py`
- Test: `tests/test_conflict_detector.py`

- [ ] **Step 1: Write deterministic conflict tests**

Create `tests/test_conflict_detector.py`:

```python
from pathlib import Path

from projectwiki.db import connect, init_db
from projectwiki.services.conflict_detector import detect_conflicts
from projectwiki.services.ingest import ingest_path
from projectwiki.services.workspace import create_project


def conflict_types(conn, project_id: str) -> set[str]:
    rows = conn.execute(
        "SELECT conflict_type FROM conflicts WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    return {row["conflict_type"] for row in rows}


def test_demo_project_conflicts(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))
    conn = connect()
    init_db(conn)
    project = create_project("Demo", conn=conn)
    root = Path(__file__).resolve().parents[1] / "examples" / "demo-project"
    ingest_path(project["id"], root, conn=conn)

    result = detect_conflicts(project["id"], conn=conn)

    assert result["conflicts_created"] >= 3
    types = conflict_types(conn, project["id"])
    assert "multiple_latest_documents" in types
    assert "endpoint_mismatch" in types
    assert "missing_mentioned_file" in types
    assert "model_architecture_mismatch" in types
```

- [ ] **Step 2: Run conflict tests**

Run:

```bash
python -m pytest tests/test_conflict_detector.py -q
```

Expected: PASS with existing rules, or FAIL if demo output is below the first-board requirement.

- [ ] **Step 3: Add deployment model mismatch rule**

Modify `projectwiki/services/conflict_detector.py`:

```python
MODEL_VERSION_RE = re.compile(r"\bmodel[_-]?v?(\d+)\b|model_v(\d+)\.pkl", re.IGNORECASE)


def detect_deployment_model_mismatch(project_id: str, conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT b.id AS block_id, b.text, s.id AS source_id, s.path
        FROM blocks b JOIN sources s ON s.id = b.source_id
        WHERE b.project_id = ?
        """,
        (project_id,),
    ).fetchall()
    deployment_hits = []
    experiment_hits = []
    for r in rows:
        text = r["text"]
        lower = text.lower()
        evidence = {"source_id": r["source_id"], "block_id": r["block_id"], "path": r["path"]}
        if any(k in lower for k in ["deploy", "deployment", "production", "部署", "线上"]):
            if MODEL_VERSION_RE.search(text) or any(w.lower() in lower for w in MODEL_WORDS):
                deployment_hits.append(evidence)
        if any(k in lower for k in ["experiment", "candidate", "f1", "accuracy", "实验"]):
            if MODEL_VERSION_RE.search(text) or any(w.lower() in lower for w in MODEL_WORDS):
                experiment_hits.append(evidence)
    if deployment_hits and experiment_hits:
        insert_conflict(
            conn,
            project_id,
            "deployment_model_mismatch",
            "部署材料与实验/候选模型记录可能不一致",
            "部署材料仍指向一个模型版本，而实验或需求材料提到了另一个候选或更新模型，需要确认线上有效模型。",
            deployment_hits[:3] + experiment_hits[:3],
            "medium",
        )
        return 1
    return 0
```

Call it from `detect_conflicts`:

```python
    inserted += detect_deployment_model_mismatch(project_id, conn)
```

- [ ] **Step 4: Assert deployment mismatch in tests**

Update `tests/test_conflict_detector.py`:

```python
    assert "deployment_model_mismatch" in types
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/test_conflict_detector.py -q
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add projectwiki/services/conflict_detector.py tests/test_conflict_detector.py
git commit -m "feat: strengthen conflict detection"
```

---

### Task 6: Evidence-Backed Ask, Wiki, And Handover

**Files:**
- Modify: `projectwiki/services/ask.py`
- Modify: `projectwiki/services/wiki_engine.py`
- Modify: `projectwiki/services/handover.py`
- Test: `tests/test_evidence_outputs.py`

- [ ] **Step 1: Write evidence output tests**

Create `tests/test_evidence_outputs.py`:

```python
from pathlib import Path

from projectwiki.services.ask import ask_project
from projectwiki.services.ingest import ingest_path
from projectwiki.services.wiki_engine import build_project
from projectwiki.services.workspace import create_project


def build_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))
    project = create_project("Demo")
    root = Path(__file__).resolve().parents[1] / "examples" / "demo-project"
    ingest_path(project["id"], root)
    build_project(project["id"])
    return project


def test_ask_returns_structured_evidence(tmp_path, monkeypatch):
    project = build_demo(tmp_path, monkeypatch)

    result = ask_project(project["id"], "接口是什么？")

    assert result["evidence"]
    assert {"kind", "id", "path", "score"}.issubset(result["evidence"][0])
    assert "证据" in result["answer"]


def test_ask_refuses_without_evidence(tmp_path, monkeypatch):
    project = build_demo(tmp_path, monkeypatch)

    result = ask_project(project["id"], "火星基地预算是多少？")

    assert result["evidence"] == []
    assert "没有找到足够证据" in result["answer"]
```

- [ ] **Step 2: Run failing or baseline tests**

Run:

```bash
python -m pytest tests/test_evidence_outputs.py -q
```

Expected: the second test may FAIL if weak token overlap returns unrelated evidence.

- [ ] **Step 3: Tighten Ask threshold**

Modify `projectwiki/services/ask.py`:

```python
MIN_SCORE = 2.0
```

Change both candidate filters:

```python
        if score >= MIN_SCORE:
            candidates.append((score, "fact", row))
```

```python
        if score >= MIN_SCORE:
            candidates.append((score, "block", row))
```

- [ ] **Step 4: Add evidence labels to generated wiki pages**

Modify `render_fact_page` in `projectwiki/services/wiki_engine.py`:

```python
        status = fact["status"]
        validity = fact["validity_status"] if "validity_status" in fact.keys() else "unknown"
        lines.append(f"  - 状态：{status}，有效性：{validity}，置信度：{fact['confidence']:.2f}")
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/test_evidence_outputs.py -q
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add projectwiki/services/ask.py projectwiki/services/wiki_engine.py projectwiki/services/handover.py tests/test_evidence_outputs.py
git commit -m "feat: tighten evidence-backed outputs"
```

---

### Task 7: Bilingual Dashboard Assets

**Files:**
- Modify: `projectwiki/static/index.html`
- Create: `projectwiki/static/styles.css`
- Create: `projectwiki/static/i18n.js`
- Create: `projectwiki/static/app.js`
- Test: `tests/test_web_assets.py`

- [ ] **Step 1: Write Web asset tests**

Create `tests/test_web_assets.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "projectwiki" / "static"


def test_dashboard_assets_exist():
    assert (STATIC / "index.html").exists()
    assert (STATIC / "styles.css").exists()
    assert (STATIC / "app.js").exists()
    assert (STATIC / "i18n.js").exists()


def test_i18n_contains_chinese_and_english_keys():
    content = (STATIC / "i18n.js").read_text(encoding="utf-8")

    assert "zh-CN" in content
    assert "en-US" in content
    assert "nav.projects" in content
    assert "action.buildWiki" in content
    assert "error.readLogs" in content
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python -m pytest tests/test_web_assets.py -q
```

Expected: FAIL because the new asset files do not exist.

- [ ] **Step 3: Add i18n dictionary**

Create `projectwiki/static/i18n.js`:

```javascript
window.ProjectWikiI18n = {
  "en-US": {
    "nav.projects": "Projects",
    "nav.sources": "Sources",
    "nav.facts": "Facts",
    "nav.wiki": "Wiki",
    "nav.conflicts": "Conflicts",
    "nav.handover": "Handover",
    "nav.ask": "Ask",
    "nav.settings": "Settings",
    "action.useDemo": "Use demo project",
    "action.createProject": "Create project",
    "action.ingest": "Ingest local folder",
    "action.buildWiki": "Build wiki",
    "empty.noProjects": "No projects yet",
    "error.readLogs": "Run projectwiki log to inspect startup logs."
  },
  "zh-CN": {
    "nav.projects": "项目",
    "nav.sources": "来源",
    "nav.facts": "事实",
    "nav.wiki": "Wiki",
    "nav.conflicts": "冲突",
    "nav.handover": "交接包",
    "nav.ask": "提问",
    "nav.settings": "设置",
    "action.useDemo": "使用示例项目",
    "action.createProject": "创建项目",
    "action.ingest": "摄入本地文件夹",
    "action.buildWiki": "生成 Wiki",
    "empty.noProjects": "还没有项目",
    "error.readLogs": "运行 projectwiki log 查看启动日志。"
  }
};
```

- [ ] **Step 4: Replace static page with dashboard shell**

Modify `projectwiki/static/index.html` to load the assets:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ProjectWiki</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <aside class="sidebar">
    <div class="brand">ProjectWiki</div>
    <nav>
      <button data-i18n="nav.projects"></button>
      <button data-i18n="nav.sources"></button>
      <button data-i18n="nav.facts"></button>
      <button data-i18n="nav.wiki"></button>
      <button data-i18n="nav.conflicts"></button>
      <button data-i18n="nav.handover"></button>
      <button data-i18n="nav.ask"></button>
      <button data-i18n="nav.settings"></button>
    </nav>
  </aside>
  <main class="workspace">
    <header class="topbar">
      <input id="search" placeholder="Search project memory" />
      <div class="language-switch">
        <button data-lang="zh-CN">中文</button>
        <button data-lang="en-US">EN</button>
      </div>
    </header>
    <section class="dashboard">
      <div class="panel">
        <h1>Project Memory</h1>
        <div class="actions">
          <button class="primary" data-i18n="action.useDemo"></button>
          <button data-i18n="action.createProject"></button>
          <button data-i18n="action.ingest"></button>
          <button data-i18n="action.buildWiki"></button>
        </div>
      </div>
      <div id="app"></div>
    </section>
  </main>
  <script src="/static/i18n.js"></script>
  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 5: Add dashboard behavior and styles**

Create `projectwiki/static/app.js`:

```javascript
const supportedLanguages = ["zh-CN", "en-US"];

function initialLanguage() {
  const saved = localStorage.getItem("projectwiki.language");
  if (supportedLanguages.includes(saved)) return saved;
  return navigator.language && navigator.language.startsWith("zh") ? "zh-CN" : "en-US";
}

function translate(lang) {
  const dict = window.ProjectWikiI18n[lang];
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = dict[node.dataset.i18n] || node.dataset.i18n;
  });
  localStorage.setItem("projectwiki.language", lang);
}

document.querySelectorAll("[data-lang]").forEach((button) => {
  button.addEventListener("click", () => translate(button.dataset.lang));
});

translate(initialLanguage());
```

Create `projectwiki/static/styles.css`:

```css
:root {
  color-scheme: light;
  --bg: #f7f7f8;
  --panel: #ffffff;
  --line: #e6e6e8;
  --text: #1f2024;
  --muted: #72747a;
  --purple: #7c3aed;
}

body {
  margin: 0;
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.sidebar {
  border-right: 1px solid var(--line);
  background: #fbfbfc;
  padding: 24px 16px;
}

.brand {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 28px;
}

.sidebar button {
  display: block;
  width: 100%;
  border: 0;
  border-radius: 8px;
  background: transparent;
  padding: 10px 12px;
  text-align: left;
  color: var(--muted);
  font: inherit;
}

.sidebar button:hover {
  background: #f0eefc;
  color: var(--text);
}

.topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid var(--line);
  background: var(--panel);
  padding: 16px 24px;
}

.topbar input {
  flex: 1;
  border: 0;
  font: inherit;
  outline: none;
}

.language-switch {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

.language-switch button {
  border: 0;
  background: var(--panel);
  padding: 8px 10px;
}

.dashboard {
  padding: 24px;
}

.panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  padding: 20px;
}

.primary {
  background: var(--purple);
  color: white;
}
```

- [ ] **Step 6: Run tests**

Run:

```bash
python -m pytest tests/test_web_assets.py -q
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add projectwiki/static/index.html projectwiki/static/styles.css projectwiki/static/i18n.js projectwiki/static/app.js tests/test_web_assets.py
git commit -m "feat: add bilingual dashboard shell"
```

---

### Task 8: Demo-First Web Flow And README

**Files:**
- Modify: `projectwiki/app.py`
- Modify: `projectwiki/static/app.js`
- Modify: `README.md`
- Test: `tests/test_demo_flow.py`

- [ ] **Step 1: Write demo API test**

Create `tests/test_demo_flow.py`:

```python
from fastapi.testclient import TestClient

from projectwiki.app import app


def test_demo_project_endpoint_builds_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    response = client.post("/api/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"]
    assert payload["ingest"]["created_blocks"] > 0
    assert payload["build"]["facts_created"] > 0
```

- [ ] **Step 2: Run failing test**

Run:

```bash
python -m pytest tests/test_demo_flow.py -q
```

Expected: FAIL because `/api/demo` does not exist.

- [ ] **Step 3: Implement demo endpoint**

Modify `projectwiki/app.py`:

```python
@app.post("/api/demo")
def api_create_demo() -> dict:
    root = Path(__file__).resolve().parents[1] / "examples" / "demo-project"
    project = create_project("Demo Project", "Messy sample project for ProjectWiki")
    ingest = ingest_path(project["id"], root)
    build = build_project(project["id"])
    return {"project": project, "ingest": ingest, "build": build}
```

- [ ] **Step 4: Wire `Use demo project` button**

Modify `projectwiki/static/app.js`:

```javascript
async function api(path, options = {}) {
  const requestOptions = Object.assign({
    headers: { "Content-Type": "application/json" },
  }, options);
  const response = await fetch(path, requestOptions);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function useDemoProject() {
  const root = document.getElementById("app");
  root.textContent = "Building demo project";
  try {
    const result = await api("/api/demo", { method: "POST" });
    root.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    root.textContent = `${error.message}\n\n${window.ProjectWikiI18n[initialLanguage()]["error.readLogs"]}`;
  }
}

document.querySelector('[data-i18n="action.useDemo"]').addEventListener("click", useDemoProject);
```

- [ ] **Step 5: Update README first-run section**

Modify `README.md` product startup section:

````markdown
## First-board product target

```bash
npm install -g projectwiki
projectwiki
```

Open the printed local URL, click `Use demo project`, then inspect Conflicts, Wiki, Handover, and Ask with evidence.
````

- [ ] **Step 6: Run tests**

Run:

```bash
python -m pytest tests/test_demo_flow.py -q
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add projectwiki/app.py projectwiki/static/app.js README.md tests/test_demo_flow.py
git commit -m "feat: add demo-first web flow"
```

---

### Task 9: Final First-Board Verification

**Files:**
- No planned modifications. If verification fails, stop at the failing command and create a focused fix before reporting completion.

- [ ] **Step 1: Run compile**

Run:

```bash
python -m compileall projectwiki
```

Expected: exit code 0.

- [ ] **Step 2: Run full tests**

Run:

```bash
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run local CLI smoke checks**

Run:

```bash
projectwiki --help
projectwiki doctor
projectwiki log
```

Expected: help prints available commands, doctor prints JSON, log prints either log content or `No ProjectWiki log file found.`

- [ ] **Step 4: Run demo through API**

Run:

```bash
python -m pytest tests/test_demo_flow.py::test_demo_project_endpoint_builds_demo -q
```

Expected: PASS.

- [ ] **Step 5: Confirm clean worktree**

Run:

```bash
git status -sb
```

Expected: no uncommitted changes after the task commits. If a verification command fails, stop and diagnose the failing command before claiming first-board completion.

---

## Plan Self-Review

Spec coverage:

- Startup and `projectwiki log`: Tasks 2 and 3.
- Schema and evidence fields: Task 1.
- API visibility: Task 4.
- Conflict algorithms: Task 5.
- Evidence-backed outputs: Task 6.
- Bilingual dashboard: Task 7.
- Demo-first Web flow: Task 8.
- Verification: Task 9.

Execution constraints:

- Each task includes tests before implementation.
- Each task has an isolated commit.
- Heavy optional dependencies remain lazy because parser dependency behavior is not changed in this plan.
- The first-board stays deterministic before LLM-heavy behavior.
