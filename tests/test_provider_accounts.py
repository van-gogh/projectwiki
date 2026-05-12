from whywiki.collaboration.accounts import AccountStore
from whywiki.collaboration.jsonio import write_json
from whywiki.collaboration.models import ProviderIdentity


def test_account_store_round_trip(tmp_path):
    store = AccountStore(tmp_path / "auth" / "accounts.json")
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="1")

    store.save_identity(identity)

    identities = store.list_identities()
    assert identities == [identity]
    assert "token" not in (tmp_path / "auth" / "accounts.json").read_text(encoding="utf-8").lower()


def test_account_store_supports_multiple_gitea_servers(tmp_path):
    store = AccountStore(tmp_path / "auth" / "accounts.json")
    store.save_identity(
        ProviderIdentity(provider="gitea", account="alice", provider_user_id="1", base_url="https://git.one.test")
    )
    store.save_identity(
        ProviderIdentity(provider="gitea", account="alice", provider_user_id="2", base_url="https://git.two.test")
    )

    provider_keys = [identity.provider_key for identity in store.list_identities()]

    assert provider_keys == ["gitea:https://git.one.test", "gitea:https://git.two.test"]


def test_account_store_replaces_same_provider_identity(tmp_path):
    store = AccountStore(tmp_path / "auth" / "accounts.json")
    store.save_identity(ProviderIdentity(provider="github", account="alice", provider_user_id="1"))
    store.save_identity(ProviderIdentity(provider="github", account="alice-renamed", provider_user_id="1"))

    identities = store.list_identities()

    assert len(identities) == 1
    assert identities[0].account == "alice-renamed"


def test_account_store_reports_provider_identity_presence(tmp_path):
    store = AccountStore(tmp_path / "auth" / "accounts.json")
    store.save_identity(
        ProviderIdentity(provider="gitea", account="alice", provider_user_id="1", base_url="https://git.one.test")
    )

    assert store.has_provider_identity("gitea:https://git.one.test")
    assert not store.has_provider_identity("gitea:https://git.two.test")


def test_account_store_supports_multiple_github_user_ids(tmp_path):
    store = AccountStore(tmp_path / "auth" / "accounts.json")
    store.save_identity(ProviderIdentity(provider="github", account="alice", provider_user_id="1"))
    store.save_identity(ProviderIdentity(provider="github", account="bob", provider_user_id="2"))

    identities = store.list_identities()

    assert identities == [
        ProviderIdentity(provider="github", account="alice", provider_user_id="1"),
        ProviderIdentity(provider="github", account="bob", provider_user_id="2"),
    ]


def test_account_store_strips_existing_token_fields_on_save(tmp_path):
    accounts_path = tmp_path / "auth" / "accounts.json"
    write_json(
        accounts_path,
        {
            "connected_accounts": [
                {
                    "provider": "github",
                    "account": "alice",
                    "provider_user_id": "1",
                    "token": "secret-token",
                }
            ],
        },
    )
    store = AccountStore(accounts_path)

    store.save_identity(ProviderIdentity(provider="github", account="alice-renamed", provider_user_id="1"))

    content = accounts_path.read_text(encoding="utf-8").lower()
    assert "token" not in content
    assert "secret" not in content
