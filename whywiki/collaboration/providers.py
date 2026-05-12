from __future__ import annotations

import json
from typing import Mapping, Protocol

from whywiki.collaboration.models import RepoPermission, RepoRef


class ProviderClient(Protocol):
    def check_repo(self, repo: RepoRef) -> RepoPermission:
        """Return the current user's permission for a repository."""


class StaticProviderClient:
    def __init__(self, permissions: Mapping[str, tuple[bool, bool]]) -> None:
        self._permissions = dict(permissions)

    def check_repo(self, repo: RepoRef) -> RepoPermission:
        can_read, can_write = self._permissions.get(repo.key, (False, False))
        return RepoPermission(repo.key, can_read, can_write)


class ProviderRegistry:
    def __init__(self) -> None:
        self._clients: dict[str, ProviderClient] = {}

    def register(self, provider_key: str, client: ProviderClient) -> None:
        self._clients[provider_key] = client

    def check_repo(self, repo: RepoRef) -> RepoPermission:
        client = self._clients.get(repo.provider_key)
        if client is None:
            return RepoPermission(
                repo.key,
                False,
                False,
                missing_provider_identity=repo.provider_key,
            )
        return client.check_repo(repo)


class GitHubProviderClient:
    def __init__(self, token: str, timeout: float = 10.0) -> None:
        self._token = token
        self._timeout = timeout

    def check_repo(self, repo: RepoRef) -> RepoPermission:
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen

        request = Request(
            f"https://api.github.com/repos/{repo.repo}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {401, 403, 404}:
                return _permission(repo, False, False)
            raise

        permissions = payload.get("permissions", {})
        can_write = bool(
            permissions.get("push")
            or permissions.get("admin")
            or permissions.get("maintain")
        )
        return _permission(repo, True, can_write)


class GiteaProviderClient:
    def __init__(self, base_url: str, token: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def check_repo(self, repo: RepoRef) -> RepoPermission:
        from urllib.error import HTTPError
        from urllib.parse import quote
        from urllib.request import Request, urlopen

        owner, name = repo.repo.split("/", maxsplit=1)
        request = Request(
            f"{self._base_url}/api/v1/repos/{quote(owner, safe='')}/{quote(name, safe='')}",
            headers={"Authorization": f"token {self._token}"},
            method="GET",
        )

        try:
            with urlopen(request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {401, 403, 404}:
                return _permission(repo, False, False)
            raise

        permissions = payload.get("permissions", {})
        can_write = bool(permissions.get("push") or permissions.get("admin"))
        return _permission(repo, True, can_write)


def _permission(repo: RepoRef, can_read: bool, can_write: bool) -> RepoPermission:
    return RepoPermission(repo.key, can_read, can_write)
