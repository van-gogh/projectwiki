from __future__ import annotations

import os
from collections.abc import Mapping

from whywiki.collaboration.providers import ProviderRegistry, StaticProviderClient


def static_permission_provider_key(repo_key: str) -> str | None:
    if repo_key.startswith("github:"):
        return "github"
    if repo_key.startswith("gitea:"):
        provider_key, repo = repo_key.rsplit(":", maxsplit=1)
        if repo and "/" in repo:
            return provider_key
    return None


def static_provider_registry_from_env(env: Mapping[str, str] | None = None) -> ProviderRegistry:
    source = env if env is not None else os.environ
    registry = ProviderRegistry()
    permissions_by_provider: dict[str, dict[str, tuple[bool, bool]]] = {}
    raw_permissions = source.get("WHYWIKI_COLLAB_STATIC_PERMISSIONS", "")
    for entry in raw_permissions.split(","):
        if "=" not in entry:
            continue
        repo_key, access = (part.strip() for part in entry.split("=", maxsplit=1))
        if access == "read":
            permission = (True, False)
        elif access == "write":
            permission = (True, True)
        else:
            continue

        provider_key = static_permission_provider_key(repo_key)
        if provider_key is None:
            continue
        permissions_by_provider.setdefault(provider_key, {})[repo_key] = permission

    for provider_key, permissions in permissions_by_provider.items():
        registry.register(provider_key, StaticProviderClient(permissions))
    return registry
