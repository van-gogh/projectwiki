from pathlib import Path
import time

from fastapi.testclient import TestClient

from whywiki.app import app
from whywiki.services.ingest import ingest_path
from whywiki.services.wiki_engine import build_project
from whywiki.services.workspace import create_project


def wait_for_job(client: TestClient, job_id: str, timeout: float = 3.0) -> dict:
    deadline = time.time() + timeout
    last_payload = {}
    while time.time() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        last_payload = response.json()
        if last_payload["status"] in {"succeeded", "failed"}:
            return last_payload
        time.sleep(0.05)
    return last_payload


def test_dashboard_api_lists_sources_facts_and_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)
    project = create_project("Fixture Project")
    root = Path(__file__).resolve().parent / "fixtures" / "messy-project"
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


def test_fact_status_update_persists_for_review_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)
    project = create_project("Fixture Project")
    root = Path(__file__).resolve().parent / "fixtures" / "messy-project"
    ingest_path(project["id"], root)
    build_project(project["id"])

    fact = client.get(f"/api/projects/{project['id']}/facts").json()[0]
    update = client.patch(
        f"/api/projects/{project['id']}/facts/{fact['id']}",
        json={"status": "confirmed"},
    )

    assert update.status_code == 200
    assert update.json()["status"] == "confirmed"
    facts = client.get(f"/api/projects/{project['id']}/facts").json()
    assert next(item for item in facts if item["id"] == fact["id"])["status"] == "confirmed"


def test_fact_evidence_endpoint_resolves_original_block_text(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)
    project = create_project("Fixture Project")
    root = Path(__file__).resolve().parent / "fixtures" / "messy-project"
    ingest_path(project["id"], root)
    build_project(project["id"])

    fact = client.get(f"/api/projects/{project['id']}/facts").json()[0]
    response = client.get(f"/api/projects/{project['id']}/facts/{fact['id']}/evidence")

    assert response.status_code == 200
    evidence = response.json()
    assert evidence
    assert {"path", "source_type", "block_text", "location"}.issubset(evidence[0])
    assert evidence[0]["block_text"]


def test_conflict_evidence_endpoint_resolves_original_block_text_when_available(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)
    project = create_project("Fixture Project")
    root = Path(__file__).resolve().parent / "fixtures" / "messy-project"
    ingest_path(project["id"], root)
    build_project(project["id"])

    conflict = client.get(f"/api/projects/{project['id']}/conflicts").json()[0]
    response = client.get(f"/api/projects/{project['id']}/conflicts/{conflict['id']}/evidence")

    assert response.status_code == 200
    evidence = response.json()
    assert evidence
    assert {"path", "source_type", "block_text", "location"}.issubset(evidence[0])


def test_ingest_and_build_jobs_expose_progress_until_success(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)
    project = create_project("Fixture Project")
    root = Path(__file__).resolve().parent / "fixtures" / "messy-project"

    ingest_start = client.post(
        f"/api/projects/{project['id']}/ingest-jobs",
        json={"path": str(root), "source_type": "local"},
    )
    assert ingest_start.status_code == 200
    ingest_payload = ingest_start.json()
    assert ingest_payload["status"] in {"queued", "running", "succeeded"}
    assert 0 <= ingest_payload["progress"] <= 100

    ingest_done = wait_for_job(client, ingest_payload["id"])
    assert ingest_done["status"] == "succeeded"
    assert ingest_done["progress"] == 100
    assert ingest_done["result"]["files_seen"] > 0

    build_start = client.post(f"/api/projects/{project['id']}/build-jobs")
    assert build_start.status_code == 200
    build_done = wait_for_job(client, build_start.json()["id"])
    assert build_done["status"] == "succeeded"
    assert build_done["progress"] == 100
    assert build_done["result"]["facts_created"] > 0
