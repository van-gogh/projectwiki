from fastapi.testclient import TestClient

from projectwiki.app import app


def test_demo_api_creates_ingests_and_builds_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))

    client = TestClient(app)
    response = client.post("/api/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"]
    assert payload["ingest"]["created_blocks"] > 0
    assert payload["build"]["facts_created"] > 0
