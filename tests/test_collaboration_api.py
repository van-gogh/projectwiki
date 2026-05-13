from fastapi.testclient import TestClient

from whywiki.app import app
from whywiki.db import connect
from whywiki.services.conflict_detector import insert_conflict
from whywiki.services.workspace import create_project


def project_with_conflict() -> tuple[str, str]:
    project = create_project("Review Project")
    with connect() as conn:
        insert_conflict(
            conn,
            project["id"],
            "review_gate_fixture",
            "人工审查权限门禁测试冲突",
            "用于验证冲突解决操作是否经过 workspace write 权限门禁。",
            [{"path": "docs/decision.md"}],
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM conflicts WHERE project_id = ?",
            (project["id"],),
        ).fetchone()
    assert row is not None
    return project["id"], row["id"]


def test_auth_accounts_endpoint_starts_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    response = client.get("/api/auth/accounts")

    assert response.status_code == 200
    assert response.json() == {"connected_accounts": []}


def test_workspace_status_reports_not_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    response = client.get("/api/workspace/status")

    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_workspace_status_reads_configured_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    create = client.post(
        "/api/workspace/connect",
        json={"provider": "github", "repo": "owner/whywiki-memory"},
    )
    status = client.get("/api/workspace/status")

    assert create.status_code == 200
    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert status.json()["workspace"]["repo"] == "owner/whywiki-memory"


def test_gitea_workspace_requires_base_url(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    response = client.post(
        "/api/workspace/connect",
        json={"provider": "gitea", "repo": "owner/whywiki-memory"},
    )

    assert response.status_code == 400
    assert "base_url" in response.json()["detail"]


def test_workspace_files_go_under_data_dir_workspace(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(data_dir))
    client = TestClient(app)

    response = client.post(
        "/api/workspace/connect",
        json={"provider": "github", "repo": "owner/whywiki-memory"},
    )

    assert response.status_code == 200
    assert (data_dir / "workspace" / "whywiki.yaml").exists()


def test_conflict_resolution_without_workspace_keeps_local_behavior(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)
    project_id, conflict_id = project_with_conflict()

    response = client.patch(
        f"/api/projects/{project_id}/conflicts/{conflict_id}",
        json={"status": "resolved"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": conflict_id, "status": "resolved"}


def test_conflict_resolution_requires_workspace_write_permission(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(
        "WHYWIKI_COLLAB_STATIC_PERMISSIONS",
        "github:owner/whywiki-memory=read",
    )
    client = TestClient(app)
    project_id, conflict_id = project_with_conflict()
    connect_response = client.post(
        "/api/workspace/connect",
        json={"provider": "github", "repo": "owner/whywiki-memory"},
    )
    assert connect_response.status_code == 200

    response = client.patch(
        f"/api/projects/{project_id}/conflicts/{conflict_id}",
        json={"status": "resolved"},
    )

    assert response.status_code == 403


def test_conflict_resolution_allows_workspace_write_permission(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(
        "WHYWIKI_COLLAB_STATIC_PERMISSIONS",
        "gitea:https://git.example.test:team/backend=write",
    )
    client = TestClient(app)
    project_id, conflict_id = project_with_conflict()
    connect_response = client.post(
        "/api/workspace/connect",
        json={
            "provider": "gitea",
            "base_url": "https://git.example.test",
            "repo": "team/backend",
        },
    )
    assert connect_response.status_code == 200

    response = client.patch(
        f"/api/projects/{project_id}/conflicts/{conflict_id}",
        json={"status": "resolved"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": conflict_id, "status": "resolved"}
