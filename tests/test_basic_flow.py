from pathlib import Path

from projectwiki.db import connect, init_db
from projectwiki.services.workspace import create_project
from projectwiki.services.ingest import ingest_path
from projectwiki.services.wiki_engine import build_project
from projectwiki.services.ask import ask_project


def test_basic_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))
    init_db()
    project = create_project("Demo")
    root = Path(__file__).resolve().parents[1] / "examples" / "demo-project"
    result = ingest_path(project["id"], root)
    assert result["created_blocks"] > 0
    build = build_project(project["id"])
    assert build["facts_created"] > 0
    answer = ask_project(project["id"], "接口是什么？")
    assert "证据" in answer["answer"]
