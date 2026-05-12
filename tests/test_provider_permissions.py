import json
from urllib.error import HTTPError

import pytest

from whywiki.collaboration.models import RepoRef
from whywiki.collaboration.providers import (
    GiteaProviderClient,
    GitHubProviderClient,
    ProviderRegistry,
    StaticProviderClient,
)


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _http_error(status_code: int) -> HTTPError:
    return HTTPError(
        url="https://provider.example.test/repo",
        code=status_code,
        msg="provider error",
        hdrs={},
        fp=None,
    )


def test_static_provider_returns_configured_permission():
    registry = ProviderRegistry()
    registry.register(
        "github",
        StaticProviderClient(
            permissions={
                "github:owner/whywiki-memory": (True, True),
                "github:owner/code": (True, False),
            }
        ),
    )

    workspace = registry.check_repo(RepoRef(provider="github", repo="owner/whywiki-memory"))
    code = registry.check_repo(RepoRef(provider="github", repo="owner/code"))

    assert workspace.can_read is True
    assert workspace.can_write is True
    assert code.can_read is True
    assert code.can_write is False


def test_registry_reports_missing_identity_for_unknown_provider_key():
    registry = ProviderRegistry()
    ref = RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test")

    permission = registry.check_repo(ref)

    assert permission.can_read is False
    assert permission.can_write is False
    assert permission.missing_provider_identity == "gitea:https://git.example.test"


def test_static_provider_reports_unknown_repo_as_unreadable():
    client = StaticProviderClient(permissions={})

    permission = client.check_repo(RepoRef(provider="github", repo="owner/missing"))

    assert permission.repo_key == "github:owner/missing"
    assert permission.can_read is False
    assert permission.can_write is False


def test_registry_uses_gitea_provider_key():
    registry = ProviderRegistry()
    registry.register(
        "gitea:https://git.example.test",
        StaticProviderClient(permissions={"gitea:https://git.example.test:team/backend": (True, True)}),
    )

    permission = registry.check_repo(RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test"))

    assert permission.can_read is True
    assert permission.can_write is True


def test_http_provider_clients_can_be_instantiated_without_network():
    GitHubProviderClient(token="github-token")
    GiteaProviderClient(base_url="https://git.example.test", token="gitea-token")


@pytest.mark.parametrize("permission_name", ["push", "admin", "maintain"])
def test_github_client_success_quotes_repo_and_reads_write_permissions(monkeypatch, permission_name):
    captured_requests = []
    token = "github-secret-token"

    def fake_urlopen(request, timeout):
        captured_requests.append(request)
        return _FakeHTTPResponse({"permissions": {permission_name: True}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    permission = GitHubProviderClient(token=token).check_repo(
        RepoRef(provider="github", repo="owner:team/repo#one?x")
    )

    request = captured_requests[0]
    assert request.get_full_url() == "https://api.github.com/repos/owner%3Ateam/repo%23one%3Fx"
    assert request.get_header("Authorization") == f"Bearer {token}"
    assert token not in request.get_full_url()
    assert permission.can_read is True
    assert permission.can_write is True


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_github_client_fail_closed_for_auth_and_missing_errors(monkeypatch, status_code):
    def fake_urlopen(request, timeout):
        raise _http_error(status_code)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    permission = GitHubProviderClient(token="github-token").check_repo(
        RepoRef(provider="github", repo="owner/repo")
    )

    assert permission.can_read is False
    assert permission.can_write is False


def test_github_client_reraises_unexpected_http_errors(monkeypatch):
    def fake_urlopen(request, timeout):
        raise _http_error(500)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(HTTPError) as error:
        GitHubProviderClient(token="github-token").check_repo(RepoRef(provider="github", repo="owner/repo"))

    assert error.value.code == 500


@pytest.mark.parametrize("permission_name", ["push", "admin"])
def test_gitea_client_success_quotes_repo_and_reads_write_permissions(monkeypatch, permission_name):
    captured_requests = []
    token = "gitea-secret-token"

    def fake_urlopen(request, timeout):
        captured_requests.append(request)
        return _FakeHTTPResponse({"permissions": {permission_name: True}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    permission = GiteaProviderClient(base_url="https://git.example.test/", token=token).check_repo(
        RepoRef(provider="gitea", repo="team:ops/backend#api?x", base_url="https://git.example.test")
    )

    request = captured_requests[0]
    assert request.get_full_url() == "https://git.example.test/api/v1/repos/team%3Aops/backend%23api%3Fx"
    assert request.get_header("Authorization") == f"token {token}"
    assert token not in request.get_full_url()
    assert permission.can_read is True
    assert permission.can_write is True


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_gitea_client_fail_closed_for_auth_and_missing_errors(monkeypatch, status_code):
    def fake_urlopen(request, timeout):
        raise _http_error(status_code)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    permission = GiteaProviderClient(base_url="https://git.example.test", token="gitea-token").check_repo(
        RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test")
    )

    assert permission.can_read is False
    assert permission.can_write is False


def test_gitea_client_reraises_unexpected_http_errors(monkeypatch):
    def fake_urlopen(request, timeout):
        raise _http_error(500)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(HTTPError) as error:
        GiteaProviderClient(base_url="https://git.example.test", token="gitea-token").check_repo(
            RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test")
        )

    assert error.value.code == 500
