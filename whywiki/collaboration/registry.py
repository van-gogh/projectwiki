from __future__ import annotations

from collections.abc import Iterable, Mapping

from .env import static_provider_registry_from_env
from .models import ProviderIdentity
from .providers import GiteaProviderClient, GitHubProviderClient, ProviderRegistry
from .tokens import TokenStore


def provider_registry_from_accounts(
    identities: Iterable[ProviderIdentity],
    token_store: TokenStore,
    env: Mapping[str, str] | None = None,
) -> ProviderRegistry:
    registry = static_provider_registry_from_env(env)
    for identity in identities:
        token = token_store.load(identity)
        if token is None:
            continue
        if identity.provider == "github":
            registry.register(identity.provider_key, GitHubProviderClient(token.access_token))
        elif identity.provider == "gitea" and identity.base_url is not None:
            registry.register(
                identity.provider_key,
                GiteaProviderClient(identity.base_url, token.access_token),
            )
    return registry
