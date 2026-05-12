from pathlib import Path

from fastapi.testclient import TestClient

from whywiki.app import app
from whywiki.services.ingest import ingest_path
from whywiki.services.wiki_engine import build_project
from whywiki.services.workspace import create_project


def test_dashboard_api_lists_sources_facts_and_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
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
