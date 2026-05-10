from fastapi.testclient import TestClient

import projectwiki.app as app_module
from projectwiki.app import app
from projectwiki.services.workspace import list_projects


def test_demo_project_root_uses_packaged_demo_assets():
    root = app_module.demo_project_root()

    assert root.name == "demo_project"
    assert "examples" not in root.parts
    assert root.is_dir()
    assert (root / "README.md").is_file()


def test_demo_api_creates_ingests_and_builds_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))

    client = TestClient(app)
    response = client.post("/api/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"]
    assert payload["ingest"]["created_blocks"] > 0
    assert payload["build"]["facts_created"] > 0


def test_demo_api_rejects_missing_demo_assets_before_creating_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(app_module, "demo_project_root", lambda: tmp_path / "missing-demo-project")

    client = TestClient(app)
    response = client.post("/api/demo")

    assert response.status_code == 500
    payload = response.json()
    assert "project" not in payload
    assert "Demo project assets not found" in payload["detail"]
    assert list_projects() == []
