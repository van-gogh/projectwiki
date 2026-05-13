from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Literal, Mapping, Sequence, cast
from urllib.parse import urlparse

ProviderName = Literal["github", "gitea"]
ReviewAction = Literal["approve", "reject", "resolve", "ignore", "note"]
ReviewSubjectType = Literal["fact", "conflict"]

_PROVIDERS = {"github", "gitea"}
_REVIEW_ACTIONS = {"approve", "reject", "resolve", "ignore", "note"}
_REVIEW_SUBJECT_TYPES = {"fact", "conflict"}


def _normalize_provider(provider: str) -> ProviderName:
    if provider not in _PROVIDERS:
        raise ValueError("provider must be 'github' or 'gitea'")
    return cast(ProviderName, provider)


def _normalize_base_url(provider: ProviderName, base_url: str | None) -> str | None:
    if provider == "github":
        return None
    if base_url is None:
        return None
    value = base_url.strip().rstrip("/")
    parsed = urlparse(value)
    if not value or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("gitea base_url must be an http(s) URL with a host")
    return value


def _normalize_repo(repo: str) -> str:
    value = repo.strip()
    parts = value.split("/")
    if len(parts) != 2 or not all(parts) or any(any(char.isspace() for char in part) for part in parts):
        raise ValueError("repo must be in owner/name form")
    return value


def _provider_key(provider: ProviderName, base_url: str | None) -> str:
    if provider == "github":
        return "github"
    if base_url is None:
        raise ValueError("gitea provider requires base_url")
    return f"gitea:{base_url}"


@dataclass(frozen=True)
class RepoRef:
    provider: ProviderName
    repo: str
    base_url: str | None = None

    def __post_init__(self) -> None:
        provider = _normalize_provider(self.provider)
        repo = _normalize_repo(self.repo)
        base_url = _normalize_base_url(provider, self.base_url)
        if provider == "gitea" and base_url is None:
            raise ValueError("gitea repo references require base_url")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "repo", repo)
        object.__setattr__(self, "base_url", base_url)

    @property
    def provider_key(self) -> str:
        return _provider_key(self.provider, self.base_url)

    @property
    def key(self) -> str:
        if self.provider == "github":
            return f"github:{self.repo}"
        return f"{self.provider_key}:{self.repo}"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": self.provider,
            "repo": self.repo,
        }
        if self.base_url is not None:
            payload["base_url"] = self.base_url
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RepoRef:
        return cls(
            provider=payload["provider"],
            repo=payload["repo"],
            base_url=payload.get("base_url"),
        )


@dataclass(frozen=True)
class LinkedRepo:
    id: str
    repo: RepoRef
    branch: str = "main"
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "provider": self.repo.provider,
            "repo": self.repo.repo,
            "branch": self.branch,
            "required": self.required,
        }
        if self.repo.base_url is not None:
            payload["base_url"] = self.repo.base_url
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LinkedRepo:
        return cls(
            id=payload["id"],
            repo=RepoRef(
                provider=payload["provider"],
                repo=payload["repo"],
                base_url=payload.get("base_url"),
            ),
            branch=payload.get("branch", "main"),
            required=payload.get("required", True),
        )


@dataclass(frozen=True)
class ProviderIdentity:
    provider: ProviderName
    account: str
    provider_user_id: str
    base_url: str | None = None

    def __post_init__(self) -> None:
        provider = _normalize_provider(self.provider)
        base_url = _normalize_base_url(provider, self.base_url)
        if provider == "gitea" and base_url is None:
            raise ValueError("gitea identities require base_url")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "base_url", base_url)

    @property
    def provider_key(self) -> str:
        return _provider_key(self.provider, self.base_url)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": self.provider,
            "account": self.account,
            "provider_user_id": self.provider_user_id,
        }
        if self.base_url is not None:
            payload["base_url"] = self.base_url
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProviderIdentity:
        return cls(
            provider=payload["provider"],
            account=payload["account"],
            provider_user_id=payload["provider_user_id"],
            base_url=payload.get("base_url"),
        )


@dataclass(frozen=True)
class RepoPermission:
    repo_key: str
    can_read: bool
    can_write: bool
    missing_provider_identity: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "repo_key": self.repo_key,
            "can_read": self.can_read,
            "can_write": self.can_write,
        }
        if self.missing_provider_identity is not None:
            payload["missing_provider_identity"] = self.missing_provider_identity
        return payload


@dataclass(frozen=True)
class WorkspaceAccessReport:
    workspace: RepoPermission
    linked_repos: Sequence[RepoPermission] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "linked_repos", tuple(self.linked_repos))

    @property
    def missing_required_linked_repo_permissions(self) -> list[RepoPermission]:
        return [permission for permission in self.linked_repos if not permission.can_read]

    @property
    def missing_required_linked_repo_access(self) -> bool:
        return bool(self.missing_required_linked_repo_permissions)

    @property
    def can_enter_workspace(self) -> bool:
        return self.workspace.can_read

    @property
    def can_review(self) -> bool:
        return self.workspace.can_read and self.workspace.can_write

    @property
    def can_view_project_memory(self) -> bool:
        return self.can_enter_workspace and not self.missing_required_linked_repo_access

    def to_dict(self) -> dict[str, Any]:
        missing_permissions = self.missing_required_linked_repo_permissions
        return {
            "workspace": self.workspace.to_dict(),
            "linked_repos": [permission.to_dict() for permission in self.linked_repos],
            "can_enter_workspace": self.can_enter_workspace,
            "can_review": self.can_review,
            "can_view_project_memory": self.can_view_project_memory,
            "missing_required_linked_repo_access": self.missing_required_linked_repo_access,
            "missing_required_linked_repo_permissions": [
                permission.to_dict() for permission in missing_permissions
            ],
        }


@dataclass(frozen=True)
class WorkspaceConfig:
    workspace: RepoRef
    projects: Mapping[str, Sequence[LinkedRepo]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        projects = MappingProxyType({slug: tuple(linked_repos) for slug, linked_repos in self.projects.items()})
        object.__setattr__(self, "projects", projects)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace.to_dict(),
            "projects": {
                slug: {"linked_repos": [linked_repo.to_dict() for linked_repo in linked_repos]}
                for slug, linked_repos in self.projects.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorkspaceConfig:
        projects: dict[str, list[LinkedRepo]] = {}
        for slug, project_payload in payload.get("projects", {}).items():
            projects[slug] = [
                LinkedRepo.from_dict(linked_repo)
                for linked_repo in project_payload.get("linked_repos", [])
            ]
        return cls(
            workspace=RepoRef.from_dict(payload["workspace"]),
            projects=projects,
        )


@dataclass(frozen=True)
class EvidencePointer:
    provider: ProviderName
    repo: str
    commit: str
    path: str
    base_url: str | None = None
    ref: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    content_hash: str | None = None
    source_id: str | None = None
    block_id: str | None = None

    def __post_init__(self) -> None:
        provider = _normalize_provider(self.provider)
        repo = _normalize_repo(self.repo)
        base_url = _normalize_base_url(provider, self.base_url)
        if provider == "gitea" and base_url is None:
            raise ValueError("gitea evidence pointers require base_url")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "repo", repo)
        object.__setattr__(self, "base_url", base_url)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": self.provider,
            "repo": self.repo,
            "commit": self.commit,
            "path": self.path,
        }
        optional_fields = (
            "base_url",
            "ref",
            "line_start",
            "line_end",
            "content_hash",
            "source_id",
            "block_id",
        )
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = value
        return payload


@dataclass(frozen=True)
class ReviewEvent:
    id: str
    project_slug: str
    subject_type: ReviewSubjectType
    subject_id: str
    action: ReviewAction
    actor: ProviderIdentity
    created_at: str | datetime
    note: str = ""

    def __post_init__(self) -> None:
        if self.subject_type not in _REVIEW_SUBJECT_TYPES:
            raise ValueError("subject_type must be 'fact' or 'conflict'")
        if self.action not in _REVIEW_ACTIONS:
            raise ValueError("action must be one of approve, reject, resolve, ignore, note")
        object.__setattr__(self, "subject_type", cast(ReviewSubjectType, self.subject_type))
        object.__setattr__(self, "action", cast(ReviewAction, self.action))

    def to_dict(self) -> dict[str, Any]:
        created_at = self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        return {
            "id": self.id,
            "project_slug": self.project_slug,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "action": self.action,
            "actor": self.actor.to_dict(),
            "created_at": created_at,
            "note": self.note,
        }
