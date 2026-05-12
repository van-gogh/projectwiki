from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, cast

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


def _normalize_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    value = base_url.strip().rstrip("/")
    return value or None


def _normalize_repo(repo: str) -> str:
    value = repo.strip()
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("repo must be in owner/name form")
    return value


def _provider_key(provider: ProviderName, base_url: str | None) -> str:
    if provider == "github":
        return "github"
    if base_url is None:
        raise ValueError("gitea provider requires base_url")
    return f"gitea:{base_url}"


@dataclass
class RepoRef:
    provider: ProviderName
    repo: str
    base_url: str | None = None

    def __post_init__(self) -> None:
        self.provider = _normalize_provider(self.provider)
        self.repo = _normalize_repo(self.repo)
        self.base_url = _normalize_base_url(self.base_url)
        if self.provider == "gitea" and self.base_url is None:
            raise ValueError("gitea repo references require base_url")

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


@dataclass
class LinkedRepo:
    id: str
    repo: RepoRef
    branch: str = "main"
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "repo": self.repo.to_dict(),
            "branch": self.branch,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LinkedRepo:
        return cls(
            id=payload["id"],
            repo=RepoRef.from_dict(payload["repo"]),
            branch=payload.get("branch", "main"),
            required=payload.get("required", True),
        )


@dataclass
class ProviderIdentity:
    provider: ProviderName
    account: str
    provider_user_id: str
    base_url: str | None = None

    def __post_init__(self) -> None:
        self.provider = _normalize_provider(self.provider)
        self.base_url = _normalize_base_url(self.base_url)
        if self.provider == "gitea" and self.base_url is None:
            raise ValueError("gitea identities require base_url")

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


@dataclass
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


@dataclass
class WorkspaceAccessReport:
    workspace: RepoPermission
    linked_repos: list[RepoPermission] = field(default_factory=list)

    @property
    def missing_required_linked_repo_access(self) -> list[RepoPermission]:
        return [permission for permission in self.linked_repos if not permission.can_read]

    @property
    def can_enter_workspace(self) -> bool:
        return self.workspace.can_read and not self.missing_required_linked_repo_access

    @property
    def can_review(self) -> bool:
        return self.can_enter_workspace and self.workspace.can_write

    def to_dict(self) -> dict[str, Any]:
        missing = self.missing_required_linked_repo_access
        return {
            "workspace": self.workspace.to_dict(),
            "linked_repos": [permission.to_dict() for permission in self.linked_repos],
            "can_enter_workspace": self.can_enter_workspace,
            "can_review": self.can_review,
            "missing_required_linked_repo_access": [permission.to_dict() for permission in missing],
        }


@dataclass
class WorkspaceConfig:
    workspace: RepoRef
    projects: dict[str, list[LinkedRepo]] = field(default_factory=dict)

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


@dataclass
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
        self.provider = _normalize_provider(self.provider)
        self.repo = _normalize_repo(self.repo)
        self.base_url = _normalize_base_url(self.base_url)
        if self.provider == "gitea" and self.base_url is None:
            raise ValueError("gitea evidence pointers require base_url")

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


@dataclass
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
        self.subject_type = cast(ReviewSubjectType, self.subject_type)
        if self.action not in _REVIEW_ACTIONS:
            raise ValueError("action must be one of approve, reject, resolve, ignore, note")
        self.action = cast(ReviewAction, self.action)

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
