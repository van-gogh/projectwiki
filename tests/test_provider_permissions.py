from whywiki.collaboration.models import RepoRef
from whywiki.collaboration.providers import (
    GiteaProviderClient,
    GitHubProviderClient,
    ProviderRegistry,
    StaticProviderClient,
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
