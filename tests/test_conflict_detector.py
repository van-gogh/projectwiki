from pathlib import Path

from projectwiki.db import connect, init_db
from projectwiki.services.conflict_detector import detect_conflicts
from projectwiki.services.ingest import ingest_path
from projectwiki.services.workspace import create_project
from projectwiki.utils import from_json


def conflict_types(conn, project_id: str) -> set[str]:
    rows = conn.execute(
        "SELECT conflict_type FROM conflicts WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    return {row["conflict_type"] for row in rows}


def conflict_row(conn, project_id: str, conflict_type: str):
    return conn.execute(
        """
        SELECT * FROM conflicts
        WHERE project_id = ? AND conflict_type = ?
        """,
        (project_id, conflict_type),
    ).fetchone()


def create_ingested_project(tmp_path, monkeypatch, files: dict[str, str]):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))
    conn = connect()
    init_db(conn)
    project = create_project("Demo", conn=conn)
    root = tmp_path / "project"
    root.mkdir()
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    ingest_path(project["id"], root, conn=conn)
    return conn, project


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
    assert "deployment_model_mismatch" in types


def test_deployment_model_mismatch_requires_different_identifiers(tmp_path, monkeypatch):
    conn, project = create_ingested_project(
        tmp_path,
        monkeypatch,
        {
            "deploy.md": "Production deployment uses LSTM model_v1.pkl.",
            "experiment.md": "Candidate experiment reached better accuracy with Transformer v2.",
        },
    )

    detect_conflicts(project["id"], conn=conn)

    row = conflict_row(conn, project["id"], "deployment_model_mismatch")
    assert row is not None
    evidence = from_json(row["evidence_json"], [])
    identifiers = [set(item["model_identifiers"]) for item in evidence]
    assert {"lstm", "v1"} in identifiers
    assert {"transformer", "v2"} in identifiers
    assert "v1" in row["description"]
    assert "v2" in row["description"]


def test_deployment_model_mismatch_ignores_matching_identifiers(tmp_path, monkeypatch):
    conn, project = create_ingested_project(
        tmp_path,
        monkeypatch,
        {
            "deploy.md": "Production deployment uses Transformer model_v2.pkl.",
            "experiment.md": "Candidate experiment accuracy is based on Transformer v2.",
        },
    )

    detect_conflicts(project["id"], conn=conn)

    assert "deployment_model_mismatch" not in conflict_types(conn, project["id"])
