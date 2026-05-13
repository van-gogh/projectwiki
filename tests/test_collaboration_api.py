from fastapi.testclient import TestClient

from whywiki.app import app


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
