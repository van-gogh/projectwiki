import json

from whywiki.cli import main


def test_auth_list_starts_empty(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))

    code = main(["auth", "list"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"connected_accounts": []}


def test_auth_login_github_persists_identity_and_does_not_print_token(tmp_path, monkeypatch, capsys):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(data_dir))

    assert main([
        "auth",
        "login",
        "github",
        "--account",
        "alice",
        "--provider-user-id",
        "42",
    ]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload == {
        "provider": "github",
        "account": "alice",
        "provider_user_id": "42",
    }
    assert "token" not in output.lower()
    assert "token" not in (data_dir / "auth" / "accounts.json").read_text(encoding="utf-8").lower()

    assert main(["auth", "list"]) == 0
    list_payload = json.loads(capsys.readouterr().out)
    assert list_payload == {"connected_accounts": [payload]}


def test_gitea_login_without_base_url_returns_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))

    code = main([
        "auth",
        "login",
        "gitea",
        "--account",
        "alice",
        "--provider-user-id",
        "42",
    ])

    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "base_url" in captured.err


def test_workspace_connect_and_status(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))

    assert main(["workspace", "connect", "github", "owner/whywiki-memory"]) == 0
    capsys.readouterr()
    assert main(["workspace", "status"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["configured"] is True
    assert payload["workspace"]["repo"] == "owner/whywiki-memory"
    assert payload["access"]["can_enter_workspace"] is False
    assert payload["access"]["workspace"]["missing_provider_identity"] == "github"


def test_workspace_connect_gitea_without_base_url_returns_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))

    code = main(["workspace", "connect", "gitea", "owner/whywiki-memory"])

    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "base_url" in captured.err


def test_workspace_status_not_configured(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))

    assert main(["workspace", "status"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {"configured": False, "workspace": None, "projects": {}, "access": None}
