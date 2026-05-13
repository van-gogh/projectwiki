import pytest
from fastapi.testclient import TestClient

from whywiki import app as app_module
from whywiki.app import app
from whywiki.collaboration.accounts import AccountStore
from whywiki.collaboration.models import ProviderIdentity
from whywiki.collaboration.tokens import FileTokenStore, KeyringTokenStore, ProviderToken


@pytest.fixture(autouse=True)
def isolate_auth_api_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("WHYWIKI_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", raising=False)
    monkeypatch.delenv("WHYWIKI_COLLAB_STATIC_PERMISSIONS", raising=False)
    monkeypatch.setattr(KeyringTokenStore, "available", lambda self: False)
    if hasattr(app_module, "auth_sessions"):
        app_module.auth_sessions._sessions.clear()


def _client() -> TestClient:
    return TestClient(app)


def _token_store(tmp_path):
    return FileTokenStore.from_env(tmp_path / "data" / "auth" / "tokens.json")


def test_github_device_start_requires_client_id_env():
    response = _client().post("/api/auth/github/device/start")

    assert response.status_code == 400
    assert "WHYWIKI_GITHUB_CLIENT_ID" in response.json()["detail"]


def test_github_device_poll_authorized_saves_identity_and_token_without_returning_token(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("WHYWIKI_GITHUB_CLIENT_ID", "github-client")
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="42")

    def fake_poll(self, device_code, current_interval=5):
        assert device_code == "device-123"
        assert current_interval == 7
        return {
            "status": "authorized",
            "provider": "github",
            "token": ProviderToken(access_token="secret-token", scope="repo"),
        }

    monkeypatch.setattr(app_module.GitHubDeviceFlowClient, "poll", fake_poll)
    monkeypatch.setattr(
        app_module.GitHubProviderClient,
        "authenticated_identity",
        lambda self: identity,
    )

    response = _client().post(
        "/api/auth/github/device/poll",
        json={"device_code": "device-123", "current_interval": 7},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "connected",
        "provider": "github",
        "identity": identity.to_dict(),
    }
    assert "secret-token" not in response.text
    assert AccountStore(tmp_path / "data" / "auth" / "accounts.json").list_identities() == [identity]
    assert _token_store(tmp_path).load(identity).access_token == "secret-token"


def test_github_device_poll_pending_passes_through_without_saving_account_or_token(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("WHYWIKI_GITHUB_CLIENT_ID", "github-client")
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")

    def fake_poll(self, device_code, current_interval=5):
        return {
            "status": "waiting_for_user",
            "provider": "github",
            "error": "authorization_pending",
            "poll_after_seconds": current_interval,
        }

    monkeypatch.setattr(app_module.GitHubDeviceFlowClient, "poll", fake_poll)

    response = _client().post(
        "/api/auth/github/device/poll",
        json={"device_code": "device-123", "current_interval": 8},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "waiting_for_user"
    assert response.json()["poll_after_seconds"] == 8
    assert AccountStore(tmp_path / "data" / "auth" / "accounts.json").list_identities() == []
    assert not (tmp_path / "data" / "auth" / "tokens.json").exists()


def test_gitea_start_requires_base_url_and_client_id():
    client = _client()

    missing_base_url = client.post(
        "/api/auth/gitea/start",
        json={"base_url": "", "client_id": "client"},
    )
    missing_client_id = client.post(
        "/api/auth/gitea/start",
        json={"base_url": "https://git.example.test", "client_id": ""},
    )

    assert missing_base_url.status_code == 400
    assert "base_url" in missing_base_url.json()["detail"]
    assert missing_client_id.status_code == 400
    assert "client_id" in missing_client_id.json()["detail"]


def test_gitea_start_stores_session_and_returns_authorization_url_without_token(monkeypatch):
    def fake_start(self):
        return {
            "status": "redirect",
            "provider": "gitea",
            "authorization_url": "https://git.example.test/login/oauth/authorize?state=state-123",
            "state": "state-123",
            "session": {"state": "state-123", "code_verifier": "verifier"},
        }

    monkeypatch.setattr(app_module.GiteaOAuthClient, "start", fake_start)

    response = _client().post(
        "/api/auth/gitea/start",
        json={"base_url": "https://git.example.test", "client_id": "gitea-client"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "redirect",
        "provider": "gitea",
        "authorization_url": "https://git.example.test/login/oauth/authorize?state=state-123",
        "state": "state-123",
    }
    assert "verifier" not in response.text
    assert app_module.auth_sessions.pop("state-123") == {"state": "state-123", "code_verifier": "verifier"}


def test_gitea_callback_invalid_state_returns_400():
    response = _client().get("/api/auth/gitea/callback?code=code-123&state=missing")

    assert response.status_code == 400
    assert "state" in response.json()["detail"]


def test_gitea_callback_success_saves_identity_and_token(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    identity = ProviderIdentity(
        provider="gitea",
        base_url="https://git.example.test",
        account="alice",
        provider_user_id="99",
    )
    app_module.auth_sessions.save(
        "state-123",
        {
            "base_url": "https://git.example.test",
            "client_id": "gitea-client",
            "redirect_uri": "http://127.0.0.1:8765/api/auth/gitea/callback",
            "code_verifier": "verifier",
        },
    )

    def fake_exchange_code(self, code, code_verifier):
        assert code == "code-123"
        assert code_verifier == "verifier"
        return ProviderToken(access_token="gitea-secret", scope="read:user")

    monkeypatch.setattr(app_module.GiteaOAuthClient, "exchange_code", fake_exchange_code)
    monkeypatch.setattr(
        app_module.GiteaProviderClient,
        "authenticated_identity",
        lambda self: identity,
    )

    response = _client().get("/api/auth/gitea/callback?code=code-123&state=state-123")

    assert response.status_code == 200
    assert "connected" in response.text.lower()
    assert "gitea-secret" not in response.text
    assert AccountStore(tmp_path / "data" / "auth" / "accounts.json").list_identities() == [identity]
    assert _token_store(tmp_path).load(identity).access_token == "gitea-secret"


def test_delete_account_removes_identity_and_token(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="42")
    AccountStore(tmp_path / "data" / "auth" / "accounts.json").save_identity(identity)
    _token_store(tmp_path).save(identity, ProviderToken(access_token="secret-token"))

    response = _client().delete("/api/auth/accounts/github%3A42")

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    assert AccountStore(tmp_path / "data" / "auth" / "accounts.json").list_identities() == []
    assert _token_store(tmp_path).load(identity) is None


def test_auth_accounts_returns_only_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="42")
    AccountStore(tmp_path / "data" / "auth" / "accounts.json").save_identity(identity)
    _token_store(tmp_path).save(identity, ProviderToken(access_token="secret-token"))

    response = _client().get("/api/auth/accounts")

    assert response.status_code == 200
    assert response.json() == {"connected_accounts": [identity.to_dict()]}
    assert "secret-token" not in response.text
