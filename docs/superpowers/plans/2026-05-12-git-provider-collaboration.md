# Git Provider Collaboration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Git-provider-backed collaboration layer for WhyWiki, where GitHub/Gitea identities and repo permissions control workspace access while `whywiki.db` stays a local rebuildable cache.

**Architecture:** Add a small `whywiki.collaboration` package for durable artifact schemas, local account records, provider permission checks, and workspace access decisions. Keep the existing FastAPI + SQLite + static UI architecture, and expose collaboration state through focused service functions, API endpoints, CLI commands, and lightweight UI status panels. The first slice stores only project-memory artifacts in the WhyWiki workspace repo and never copies linked code repos into it.

**Tech Stack:** Python 3.10+, dataclasses, JSON/JSONL files, FastAPI, SQLite, pytest, vanilla HTML/CSS/JS, Git provider HTTP APIs through lazy standard-library requests wrappers.

---

## Scope Note

The design covers identity, permissions, workspace artifacts, linked repos, UI, CLI, review events, and secure LLM access. This plan implements the first shippable collaboration foundation:

- typed collaboration models
- Git-backed workspace artifact layout
- local connected-account records without committing secrets
- provider permission abstraction for GitHub and Gitea
- workspace and linked-repo access gates
- review/resolve permission checks
- API, CLI, and UI surfaces that expose account and permission state
- evidence pointer shape that can reference provider repo, commit, path, and line range

This plan does not add source-repo write actions, PR creation, enterprise roles, hosted storage, vector sync, or direct LLM repo access.

## File Structure

Create or modify these files:

- Create: `whywiki/collaboration/__init__.py`  
  Package marker and public exports.
- Create: `whywiki/collaboration/models.py`  
  Dataclasses for provider identities, repository refs, linked repos, workspace configs, repo permissions, permission reports, evidence pointers, and review events.
- Create: `whywiki/collaboration/jsonio.py`  
  Small JSON and JSONL read/write helpers for deterministic artifact files.
- Create: `whywiki/collaboration/artifacts.py`  
  Workspace artifact paths, load/save functions, and project-memory export helpers.
- Create: `whywiki/collaboration/accounts.py`  
  Local connected-account metadata store under the WhyWiki data directory. Tokens are intentionally excluded from persisted artifacts in this slice.
- Create: `whywiki/collaboration/providers.py`  
  Provider client protocol, GitHub/Gitea HTTP clients, and a static test client for deterministic tests.
- Create: `whywiki/services/collaboration.py`  
  Application service that combines workspace config, connected accounts, provider clients, and access rules.
- Modify: `whywiki/models.py`  
  Add provider-aware evidence pointer dataclass while preserving the current fields used by existing code.
- Modify: `whywiki/services/ask.py`  
  Include provider evidence fields in structured ask results when present.
- Modify: `whywiki/app.py`  
  Add collaboration endpoints and gate approve/resolve through the collaboration service when a workspace is active.
- Modify: `whywiki/cli.py`  
  Add `auth list`, `auth login`, `workspace connect`, and `workspace status` command groups.
- Modify: `whywiki/static/index.html`  
  Add account and workspace status containers.
- Modify: `whywiki/static/i18n.js`  
  Add English and Chinese copy for Git provider login, missing access, workspace status, and linked repo status.
- Modify: `whywiki/static/app.js`  
  Fetch and render connected accounts and workspace permission state.
- Modify: `whywiki/static/styles.css`  
  Add compact permission/status styling that matches the current dashboard.
- Test: `tests/test_collaboration_models.py`
- Test: `tests/test_workspace_artifacts.py`
- Test: `tests/test_provider_accounts.py`
- Test: `tests/test_provider_permissions.py`
- Test: `tests/test_collaboration_access.py`
- Test: `tests/test_collaboration_api.py`
- Test: `tests/test_collaboration_cli.py`
- Test: `tests/test_web_assets.py`

---

### Task 1: Collaboration Model Contracts

**Files:**
- Create: `whywiki/collaboration/__init__.py`
- Create: `whywiki/collaboration/models.py`
- Test: `tests/test_collaboration_models.py`

- [ ] **Step 1: Write failing model tests**

Create `tests/test_collaboration_models.py`:

```python
from whywiki.collaboration.models import (
    EvidencePointer,
    LinkedRepo,
    ProviderIdentity,
    RepoPermission,
    RepoRef,
    WorkspaceConfig,
)


def test_repo_ref_requires_gitea_base_url():
    ref = RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test")

    assert ref.provider == "gitea"
    assert ref.base_url == "https://git.example.test"
    assert ref.key == "gitea:https://git.example.test:team/backend"


def test_repo_ref_normalizes_github_key_without_base_url():
    ref = RepoRef(provider="github", repo="owner/project")

    assert ref.base_url is None
    assert ref.key == "github:owner/project"


def test_workspace_config_round_trip():
    config = WorkspaceConfig(
        workspace=RepoRef(provider="github", repo="owner/whywiki-memory"),
        projects={
            "demo": [
                LinkedRepo(
                    id="backend",
                    repo=RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test"),
                    branch="main",
                    required=True,
                )
            ]
        },
    )

    payload = config.to_dict()
    restored = WorkspaceConfig.from_dict(payload)

    assert restored.workspace.repo == "owner/whywiki-memory"
    assert restored.projects["demo"][0].id == "backend"
    assert restored.projects["demo"][0].required is True


def test_repo_permission_and_identity_shapes():
    identity = ProviderIdentity(
        provider="gitea",
        account="alice",
        provider_user_id="42",
        base_url="https://git.example.test",
    )
    permission = RepoPermission(repo_key="gitea:https://git.example.test:team/backend", can_read=True, can_write=False)

    assert identity.provider_key == "gitea:https://git.example.test"
    assert permission.can_read is True
    assert permission.can_write is False


def test_evidence_pointer_has_provider_location():
    pointer = EvidencePointer(
        provider="github",
        repo="owner/project",
        commit="abc123",
        path="src/app.py",
        line_start=3,
        line_end=8,
        content_hash="sha256:abc",
        source_id="src_1",
        block_id="blk_1",
    )

    assert pointer.to_dict()["provider"] == "github"
    assert pointer.to_dict()["line_start"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_collaboration_models.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'whywiki.collaboration'`.

- [ ] **Step 3: Create collaboration package exports**

Create `whywiki/collaboration/__init__.py`:

```python
from .models import (
    EvidencePointer,
    LinkedRepo,
    ProviderIdentity,
    RepoPermission,
    RepoRef,
    ReviewEvent,
    WorkspaceAccessReport,
    WorkspaceConfig,
)

__all__ = [
    "EvidencePointer",
    "LinkedRepo",
    "ProviderIdentity",
    "RepoPermission",
    "RepoRef",
    "ReviewEvent",
    "WorkspaceAccessReport",
    "WorkspaceConfig",
]
```

- [ ] **Step 4: Implement model dataclasses**

Create `whywiki/collaboration/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ProviderName = Literal["github", "gitea"]


def _clean_base_url(value: str | None) -> str | None:
    if not value:
        return None
    return value.rstrip("/")


@dataclass(frozen=True)
class RepoRef:
    provider: ProviderName
    repo: str
    base_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", _clean_base_url(self.base_url))
        if self.provider == "gitea" and not self.base_url:
            raise ValueError("Gitea repositories require base_url")
        if "/" not in self.repo:
            raise ValueError("Repository must be in owner/name form")

    @property
    def provider_key(self) -> str:
        if self.provider == "gitea":
            return f"gitea:{self.base_url}"
        return self.provider

    @property
    def key(self) -> str:
        if self.provider == "gitea":
            return f"gitea:{self.base_url}:{self.repo}"
        return f"{self.provider}:{self.repo}"

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"provider": self.provider, "repo": self.repo}
        if self.base_url:
            data["base_url"] = self.base_url
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepoRef":
        return cls(provider=data["provider"], repo=data["repo"], base_url=data.get("base_url"))


@dataclass(frozen=True)
class LinkedRepo:
    id: str
    repo: RepoRef
    branch: str = "main"
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, **self.repo.to_dict(), "branch": self.branch, "required": self.required}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LinkedRepo":
        return cls(
            id=data["id"],
            repo=RepoRef.from_dict(data),
            branch=data.get("branch", "main"),
            required=bool(data.get("required", True)),
        )


@dataclass(frozen=True)
class ProviderIdentity:
    provider: ProviderName
    account: str
    provider_user_id: str
    base_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", _clean_base_url(self.base_url))
        if self.provider == "gitea" and not self.base_url:
            raise ValueError("Gitea identities require base_url")

    @property
    def provider_key(self) -> str:
        if self.provider == "gitea":
            return f"gitea:{self.base_url}"
        return self.provider

    def to_dict(self) -> dict[str, Any]:
        data = {
            "provider": self.provider,
            "account": self.account,
            "provider_user_id": self.provider_user_id,
        }
        if self.base_url:
            data["base_url"] = self.base_url
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderIdentity":
        return cls(
            provider=data["provider"],
            account=data["account"],
            provider_user_id=data["provider_user_id"],
            base_url=data.get("base_url"),
        )


@dataclass(frozen=True)
class RepoPermission:
    repo_key: str
    can_read: bool
    can_write: bool
    missing_provider_identity: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_key": self.repo_key,
            "can_read": self.can_read,
            "can_write": self.can_write,
            "missing_provider_identity": self.missing_provider_identity,
        }


@dataclass(frozen=True)
class WorkspaceAccessReport:
    workspace: RepoPermission
    linked_repos: list[RepoPermission] = field(default_factory=list)

    @property
    def can_enter_workspace(self) -> bool:
        return self.workspace.can_read

    @property
    def can_review(self) -> bool:
        return self.workspace.can_read and self.workspace.can_write

    @property
    def missing_required_linked_repo_access(self) -> bool:
        return any(not permission.can_read for permission in self.linked_repos)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace.to_dict(),
            "linked_repos": [permission.to_dict() for permission in self.linked_repos],
            "can_enter_workspace": self.can_enter_workspace,
            "can_review": self.can_review,
            "missing_required_linked_repo_access": self.missing_required_linked_repo_access,
        }


@dataclass(frozen=True)
class WorkspaceConfig:
    workspace: RepoRef
    projects: dict[str, list[LinkedRepo]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace.to_dict(),
            "projects": {
                slug: {"linked_repos": [linked.to_dict() for linked in linked_repos]}
                for slug, linked_repos in sorted(self.projects.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceConfig":
        projects = {
            slug: [LinkedRepo.from_dict(item) for item in project.get("linked_repos", [])]
            for slug, project in data.get("projects", {}).items()
        }
        return cls(workspace=RepoRef.from_dict(data["workspace"]), projects=projects)


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

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "provider": self.provider,
            "repo": self.repo,
            "commit": self.commit,
            "path": self.path,
        }
        for key in ("base_url", "ref", "line_start", "line_end", "content_hash", "source_id", "block_id"):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        return data


@dataclass(frozen=True)
class ReviewEvent:
    id: str
    project_slug: str
    subject_type: Literal["fact", "conflict"]
    subject_id: str
    action: Literal["approve", "reject", "resolve", "ignore", "note"]
    actor: ProviderIdentity
    created_at: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_slug": self.project_slug,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "action": self.action,
            "actor": self.actor.to_dict(),
            "created_at": self.created_at,
            "note": self.note,
        }
```

- [ ] **Step 5: Run model tests**

Run:

```bash
python -m pytest tests/test_collaboration_models.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add whywiki/collaboration/__init__.py whywiki/collaboration/models.py tests/test_collaboration_models.py
git commit -m "feat: add collaboration model contracts"
```

---

### Task 2: Workspace Artifact Files

**Files:**
- Create: `whywiki/collaboration/jsonio.py`
- Create: `whywiki/collaboration/artifacts.py`
- Test: `tests/test_workspace_artifacts.py`

- [ ] **Step 1: Write failing artifact tests**

Create `tests/test_workspace_artifacts.py`:

```python
from whywiki.collaboration.artifacts import (
    WorkspaceArtifactPaths,
    load_workspace_config,
    save_review_event,
    save_workspace_config,
    workspace_project_dir,
)
from whywiki.collaboration.models import LinkedRepo, ProviderIdentity, RepoRef, ReviewEvent, WorkspaceConfig


def test_workspace_config_writes_expected_files(tmp_path):
    paths = WorkspaceArtifactPaths(tmp_path)
    config = WorkspaceConfig(
        workspace=RepoRef(provider="github", repo="owner/whywiki-memory"),
        projects={
            "demo": [
                LinkedRepo(
                    id="backend",
                    repo=RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test"),
                    branch="main",
                )
            ]
        },
    )

    save_workspace_config(paths, config)
    restored = load_workspace_config(paths)

    assert (tmp_path / "whywiki.yaml").exists()
    assert (tmp_path / "projects" / "demo" / "linked-repos.yaml").exists()
    assert restored.workspace.repo == "owner/whywiki-memory"
    assert restored.projects["demo"][0].repo.key == "gitea:https://git.example.test:team/backend"


def test_review_events_are_append_only_jsonl(tmp_path):
    paths = WorkspaceArtifactPaths(tmp_path)
    actor = ProviderIdentity(provider="github", account="alice", provider_user_id="1")
    event = ReviewEvent(
        id="rev_1",
        project_slug="demo",
        subject_type="conflict",
        subject_id="conf_1",
        action="resolve",
        actor=actor,
        created_at="2026-05-12T00:00:00Z",
        note="Confirmed in deployment docs.",
    )

    save_review_event(paths, event)
    save_review_event(paths, event)

    event_path = workspace_project_dir(paths, "demo") / "review-events.jsonl"
    lines = event_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert '"action": "resolve"' in lines[0]


def test_workspace_paths_do_not_create_code_repo_or_database_files(tmp_path):
    paths = WorkspaceArtifactPaths(tmp_path)

    workspace_project_dir(paths, "demo")

    assert not (tmp_path / "whywiki.db").exists()
    assert not (tmp_path / "repos").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_workspace_artifacts.py -q
```

Expected: FAIL because `whywiki.collaboration.artifacts` does not exist.

- [ ] **Step 3: Implement deterministic JSON helpers**

Create `whywiki/collaboration/jsonio.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
```

- [ ] **Step 4: Implement workspace artifact paths**

Create `whywiki/collaboration/artifacts.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .jsonio import append_jsonl, read_json, write_json
from .models import ReviewEvent, WorkspaceConfig


@dataclass(frozen=True)
class WorkspaceArtifactPaths:
    root: Path

    @property
    def workspace_config_path(self) -> Path:
        return self.root / "whywiki.yaml"

    @property
    def projects_dir(self) -> Path:
        return self.root / "projects"


def workspace_project_dir(paths: WorkspaceArtifactPaths, project_slug: str) -> Path:
    project_dir = paths.projects_dir / project_slug
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "wiki").mkdir(parents=True, exist_ok=True)
    (project_dir / "ask").mkdir(parents=True, exist_ok=True)
    return project_dir


def save_workspace_config(paths: WorkspaceArtifactPaths, config: WorkspaceConfig) -> None:
    write_json(paths.workspace_config_path, {"workspace": config.workspace.to_dict()})
    for project_slug, linked_repos in sorted(config.projects.items()):
        project_dir = workspace_project_dir(paths, project_slug)
        write_json(
            project_dir / "linked-repos.yaml",
            {"linked_repos": [linked_repo.to_dict() for linked_repo in linked_repos]},
        )


def load_workspace_config(paths: WorkspaceArtifactPaths) -> WorkspaceConfig:
    workspace_payload = read_json(paths.workspace_config_path)
    projects: dict[str, dict] = {}
    if paths.projects_dir.exists():
        for project_dir in sorted(path for path in paths.projects_dir.iterdir() if path.is_dir()):
            linked_path = project_dir / "linked-repos.yaml"
            if linked_path.exists():
                projects[project_dir.name] = read_json(linked_path)
    return WorkspaceConfig.from_dict({"workspace": workspace_payload["workspace"], "projects": projects})


def save_review_event(paths: WorkspaceArtifactPaths, event: ReviewEvent) -> None:
    project_dir = workspace_project_dir(paths, event.project_slug)
    append_jsonl(project_dir / "review-events.jsonl", event.to_dict())
```

- [ ] **Step 5: Run artifact tests**

Run:

```bash
python -m pytest tests/test_workspace_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add whywiki/collaboration/jsonio.py whywiki/collaboration/artifacts.py tests/test_workspace_artifacts.py
git commit -m "feat: add workspace artifact files"
```

---

### Task 3: Local Connected Account Store

**Files:**
- Create: `whywiki/collaboration/accounts.py`
- Test: `tests/test_provider_accounts.py`

- [ ] **Step 1: Write failing account store tests**

Create `tests/test_provider_accounts.py`:

```python
from whywiki.collaboration.accounts import AccountStore
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_provider_accounts.py -q
```

Expected: FAIL because `AccountStore` does not exist.

- [ ] **Step 3: Implement local account metadata store**

Create `whywiki/collaboration/accounts.py`:

```python
from __future__ import annotations

from pathlib import Path

from .jsonio import read_json, write_json
from .models import ProviderIdentity


class AccountStore:
    def __init__(self, path: Path):
        self.path = path

    def list_identities(self) -> list[ProviderIdentity]:
        if not self.path.exists():
            return []
        payload = read_json(self.path)
        return [ProviderIdentity.from_dict(item) for item in payload.get("connected_accounts", [])]

    def save_identity(self, identity: ProviderIdentity) -> None:
        identities = [
            existing
            for existing in self.list_identities()
            if not (
                existing.provider == identity.provider
                and existing.provider_user_id == identity.provider_user_id
                and existing.base_url == identity.base_url
            )
        ]
        identities.append(identity)
        identities.sort(key=lambda item: (item.provider, item.base_url or "", item.account))
        write_json(self.path, {"connected_accounts": [item.to_dict() for item in identities]})

    def has_provider_identity(self, provider_key: str) -> bool:
        return any(identity.provider_key == provider_key for identity in self.list_identities())
```

- [ ] **Step 4: Run account tests**

Run:

```bash
python -m pytest tests/test_provider_accounts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add whywiki/collaboration/accounts.py tests/test_provider_accounts.py
git commit -m "feat: add provider account store"
```

---

### Task 4: Provider Permission Checks

**Files:**
- Create: `whywiki/collaboration/providers.py`
- Test: `tests/test_provider_permissions.py`

- [ ] **Step 1: Write failing provider permission tests**

Create `tests/test_provider_permissions.py`:

```python
from whywiki.collaboration.models import RepoRef
from whywiki.collaboration.providers import ProviderRegistry, StaticProviderClient


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_provider_permissions.py -q
```

Expected: FAIL because `whywiki.collaboration.providers` does not exist.

- [ ] **Step 3: Implement provider registry and static client**

Create `whywiki/collaboration/providers.py`:

```python
from __future__ import annotations

from typing import Protocol

from .models import RepoPermission, RepoRef


class ProviderClient(Protocol):
    def check_repo(self, repo: RepoRef) -> RepoPermission:
        ...


class StaticProviderClient:
    def __init__(self, permissions: dict[str, tuple[bool, bool]]):
        self.permissions = permissions

    def check_repo(self, repo: RepoRef) -> RepoPermission:
        can_read, can_write = self.permissions.get(repo.key, (False, False))
        return RepoPermission(repo_key=repo.key, can_read=can_read, can_write=can_write)


class ProviderRegistry:
    def __init__(self) -> None:
        self._clients: dict[str, ProviderClient] = {}

    def register(self, provider_key: str, client: ProviderClient) -> None:
        self._clients[provider_key] = client

    def check_repo(self, repo: RepoRef) -> RepoPermission:
        client = self._clients.get(repo.provider_key)
        if client is None:
            return RepoPermission(
                repo_key=repo.key,
                can_read=False,
                can_write=False,
                missing_provider_identity=repo.provider_key,
            )
        return client.check_repo(repo)
```

- [ ] **Step 4: Add HTTP client skeletons without using them in tests**

Append to `whywiki/collaboration/providers.py`:

```python
class GitHubProviderClient:
    def __init__(self, token: str):
        self.token = token

    def check_repo(self, repo: RepoRef) -> RepoPermission:
        import json
        import urllib.error
        import urllib.request

        request = urllib.request.Request(
            f"https://api.github.com/repos/{repo.repo}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "WhyWiki",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403, 404}:
                return RepoPermission(repo_key=repo.key, can_read=False, can_write=False)
            raise
        permissions = payload.get("permissions") or {}
        return RepoPermission(
            repo_key=repo.key,
            can_read=True,
            can_write=bool(permissions.get("push") or permissions.get("admin") or permissions.get("maintain")),
        )


class GiteaProviderClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def check_repo(self, repo: RepoRef) -> RepoPermission:
        import json
        import urllib.error
        import urllib.parse
        import urllib.request

        owner, name = repo.repo.split("/", 1)
        path = f"{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(name, safe='')}"
        request = urllib.request.Request(
            f"{self.base_url}/api/v1/repos/{path}",
            headers={
                "Accept": "application/json",
                "Authorization": f"token {self.token}",
                "User-Agent": "WhyWiki",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403, 404}:
                return RepoPermission(repo_key=repo.key, can_read=False, can_write=False)
            raise
        permissions = payload.get("permissions") or {}
        return RepoPermission(
            repo_key=repo.key,
            can_read=True,
            can_write=bool(permissions.get("push") or permissions.get("admin")),
        )
```

- [ ] **Step 5: Run provider tests**

Run:

```bash
python -m pytest tests/test_provider_permissions.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add whywiki/collaboration/providers.py tests/test_provider_permissions.py
git commit -m "feat: add provider permission checks"
```

---

### Task 5: Workspace Access Service

**Files:**
- Create: `whywiki/services/collaboration.py`
- Test: `tests/test_collaboration_access.py`

- [ ] **Step 1: Write failing access service tests**

Create `tests/test_collaboration_access.py`:

```python
from whywiki.collaboration.models import LinkedRepo, RepoRef, WorkspaceConfig
from whywiki.collaboration.providers import ProviderRegistry, StaticProviderClient
from whywiki.services.collaboration import CollaborationService


def test_workspace_read_controls_entry():
    config = WorkspaceConfig(workspace=RepoRef(provider="github", repo="owner/whywiki-memory"))
    registry = ProviderRegistry()
    registry.register("github", StaticProviderClient({"github:owner/whywiki-memory": (False, False)}))
    service = CollaborationService(config=config, providers=registry)

    report = service.check_workspace(project_slug=None)

    assert report.can_enter_workspace is False
    assert report.can_review is False


def test_workspace_write_controls_review_permission():
    config = WorkspaceConfig(workspace=RepoRef(provider="github", repo="owner/whywiki-memory"))
    registry = ProviderRegistry()
    registry.register("github", StaticProviderClient({"github:owner/whywiki-memory": (True, False)}))
    service = CollaborationService(config=config, providers=registry)

    report = service.check_workspace(project_slug=None)

    assert report.can_enter_workspace is True
    assert report.can_review is False


def test_missing_linked_repo_blocks_source_derived_project_memory():
    config = WorkspaceConfig(
        workspace=RepoRef(provider="github", repo="owner/whywiki-memory"),
        projects={
            "demo": [
                LinkedRepo(id="backend", repo=RepoRef(provider="github", repo="owner/code"), required=True),
            ]
        },
    )
    registry = ProviderRegistry()
    registry.register(
        "github",
        StaticProviderClient(
            {
                "github:owner/whywiki-memory": (True, True),
                "github:owner/code": (False, False),
            }
        ),
    )
    service = CollaborationService(config=config, providers=registry)

    report = service.check_workspace(project_slug="demo")

    assert report.can_enter_workspace is True
    assert report.can_review is True
    assert report.missing_required_linked_repo_access is True
    assert report.linked_repos[0].repo_key == "github:owner/code"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_collaboration_access.py -q
```

Expected: FAIL because `whywiki.services.collaboration` does not exist.

- [ ] **Step 3: Implement collaboration access service**

Create `whywiki/services/collaboration.py`:

```python
from __future__ import annotations

from whywiki.collaboration.models import WorkspaceAccessReport, WorkspaceConfig
from whywiki.collaboration.providers import ProviderRegistry


class CollaborationService:
    def __init__(self, config: WorkspaceConfig, providers: ProviderRegistry):
        self.config = config
        self.providers = providers

    def check_workspace(self, project_slug: str | None) -> WorkspaceAccessReport:
        workspace_permission = self.providers.check_repo(self.config.workspace)
        linked_permissions = []
        if project_slug is not None:
            for linked_repo in self.config.projects.get(project_slug, []):
                permission = self.providers.check_repo(linked_repo.repo)
                if linked_repo.required:
                    linked_permissions.append(permission)
        return WorkspaceAccessReport(workspace=workspace_permission, linked_repos=linked_permissions)

    def require_workspace_read(self, project_slug: str | None = None) -> WorkspaceAccessReport:
        report = self.check_workspace(project_slug)
        if not report.can_enter_workspace:
            raise PermissionError("The current Git provider identity cannot read this WhyWiki workspace repo.")
        return report

    def require_review_access(self, project_slug: str | None = None) -> WorkspaceAccessReport:
        report = self.require_workspace_read(project_slug)
        if not report.can_review:
            raise PermissionError("The current Git provider identity cannot write this WhyWiki workspace repo.")
        if report.missing_required_linked_repo_access:
            raise PermissionError("The current Git provider identity cannot read all required linked source repos.")
        return report
```

- [ ] **Step 4: Run access tests**

Run:

```bash
python -m pytest tests/test_collaboration_access.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add whywiki/services/collaboration.py tests/test_collaboration_access.py
git commit -m "feat: add workspace access service"
```

---

### Task 6: Collaboration API Endpoints

**Files:**
- Modify: `whywiki/app.py`
- Test: `tests/test_collaboration_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_collaboration_api.py`:

```python
from fastapi.testclient import TestClient

from whywiki.app import app


def test_auth_accounts_endpoint_starts_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    response = client.get("/api/auth/accounts")

    assert response.status_code == 200
    assert response.json() == {"connected_accounts": []}


def test_workspace_status_reports_not_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    response = client.get("/api/workspace/status")

    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_workspace_status_reads_configured_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    create = client.post(
        "/api/workspace/connect",
        json={"provider": "github", "repo": "owner/whywiki-memory"},
    )
    status = client.get("/api/workspace/status")

    assert create.status_code == 200
    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert status.json()["workspace"]["repo"] == "owner/whywiki-memory"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_collaboration_api.py -q
```

Expected: FAIL because the collaboration API endpoints do not exist.

- [ ] **Step 3: Add request models and local helper functions**

Modify `whywiki/app.py` imports and models:

```python
from .collaboration.accounts import AccountStore
from .collaboration.artifacts import WorkspaceArtifactPaths, load_workspace_config, save_workspace_config
from .collaboration.models import RepoRef, WorkspaceConfig
from .config import get_data_dir


class ConnectWorkspaceRequest(BaseModel):
    provider: str
    repo: str
    base_url: str | None = None


def account_store() -> AccountStore:
    return AccountStore(get_data_dir() / "auth" / "accounts.json")


def workspace_paths() -> WorkspaceArtifactPaths:
    return WorkspaceArtifactPaths(get_data_dir() / "workspace")
```

- [ ] **Step 4: Add collaboration endpoints**

Append to `whywiki/app.py`:

```python
@app.get("/api/auth/accounts")
def api_auth_accounts() -> dict:
    return {"connected_accounts": [identity.to_dict() for identity in account_store().list_identities()]}


@app.post("/api/workspace/connect")
def api_workspace_connect(req: ConnectWorkspaceRequest) -> dict:
    try:
        config = WorkspaceConfig(workspace=RepoRef(provider=req.provider, repo=req.repo, base_url=req.base_url))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_workspace_config(workspace_paths(), config)
    return {"workspace": config.workspace.to_dict()}


@app.get("/api/workspace/status")
def api_workspace_status() -> dict:
    paths = workspace_paths()
    if not paths.workspace_config_path.exists():
        return {"configured": False, "workspace": None, "projects": {}}
    config = load_workspace_config(paths)
    return {"configured": True, **config.to_dict()}
```

- [ ] **Step 5: Run API tests**

Run:

```bash
python -m pytest tests/test_collaboration_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Run existing API surface tests**

Run:

```bash
python -m pytest tests/test_api_surface.py tests/test_collaboration_api.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add whywiki/app.py tests/test_collaboration_api.py
git commit -m "feat: add collaboration api endpoints"
```

---

### Task 7: Collaboration CLI Commands

**Files:**
- Modify: `whywiki/cli.py`
- Test: `tests/test_collaboration_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_collaboration_cli.py`:

```python
import json

from whywiki.cli import main


def test_auth_list_starts_empty(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))

    code = main(["auth", "list"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"connected_accounts": []}


def test_workspace_connect_and_status(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))

    assert main(["workspace", "connect", "github", "owner/whywiki-memory"]) == 0
    capsys.readouterr()
    assert main(["workspace", "status"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["configured"] is True
    assert payload["workspace"]["repo"] == "owner/whywiki-memory"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_collaboration_cli.py -q
```

Expected: FAIL because `auth` and `workspace` command groups are not registered.

- [ ] **Step 3: Add CLI imports and subcommands**

Modify `whywiki/cli.py` imports:

```python
from .collaboration.accounts import AccountStore
from .collaboration.artifacts import WorkspaceArtifactPaths, load_workspace_config, save_workspace_config
from .collaboration.models import ProviderIdentity, RepoRef, WorkspaceConfig
from .config import get_data_dir
```

Add subcommands after existing parser setup:

```python
    p_auth = sub.add_parser("auth")
    auth_sub = p_auth.add_subparsers(dest="auth_command", required=True)
    auth_sub.add_parser("list")
    p_auth_login = auth_sub.add_parser("login")
    p_auth_login.add_argument("provider", choices=["github", "gitea"])
    p_auth_login.add_argument("--account", required=True)
    p_auth_login.add_argument("--provider-user-id", required=True)
    p_auth_login.add_argument("--base-url")

    p_workspace = sub.add_parser("workspace")
    workspace_sub = p_workspace.add_subparsers(dest="workspace_command", required=True)
    p_workspace_connect = workspace_sub.add_parser("connect")
    p_workspace_connect.add_argument("provider", choices=["github", "gitea"])
    p_workspace_connect.add_argument("repo")
    p_workspace_connect.add_argument("--base-url")
    workspace_sub.add_parser("status")
```

- [ ] **Step 4: Add CLI command handlers**

Add command handling before `return 1`:

```python
    if args.command == "auth":
        store = AccountStore(get_data_dir() / "auth" / "accounts.json")
        if args.auth_command == "list":
            print(json.dumps({"connected_accounts": [item.to_dict() for item in store.list_identities()]}, ensure_ascii=False, indent=2))
            return 0
        if args.auth_command == "login":
            try:
                identity = ProviderIdentity(
                    provider=args.provider,
                    account=args.account,
                    provider_user_id=args.provider_user_id,
                    base_url=args.base_url,
                )
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            store.save_identity(identity)
            print(json.dumps(identity.to_dict(), ensure_ascii=False, indent=2))
            return 0

    if args.command == "workspace":
        paths = WorkspaceArtifactPaths(get_data_dir() / "workspace")
        if args.workspace_command == "connect":
            try:
                config = WorkspaceConfig(workspace=RepoRef(provider=args.provider, repo=args.repo, base_url=args.base_url))
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            save_workspace_config(paths, config)
            print(json.dumps({"workspace": config.workspace.to_dict()}, ensure_ascii=False, indent=2))
            return 0
        if args.workspace_command == "status":
            if not paths.workspace_config_path.exists():
                print(json.dumps({"configured": False, "workspace": None, "projects": {}}, ensure_ascii=False, indent=2))
                return 0
            config = load_workspace_config(paths)
            print(json.dumps({"configured": True, **config.to_dict()}, ensure_ascii=False, indent=2))
            return 0
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
python -m pytest tests/test_collaboration_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Run runtime CLI tests**

Run:

```bash
python -m pytest tests/test_runtime_cli.py tests/test_collaboration_cli.py -q
```

Expected: PASS. In restricted sandboxes, rerun the same command with approval if socket binding is blocked.

- [ ] **Step 7: Commit**

```bash
git add whywiki/cli.py tests/test_collaboration_cli.py
git commit -m "feat: add collaboration cli commands"
```

---

### Task 8: Provider-Aware Evidence Output

**Files:**
- Modify: `whywiki/models.py`
- Modify: `whywiki/services/ask.py`
- Test: `tests/test_evidence_outputs.py`

- [ ] **Step 1: Add failing evidence pointer test**

Append to `tests/test_evidence_outputs.py`:

```python
from whywiki.collaboration.models import EvidencePointer as ProviderEvidencePointer


def test_provider_evidence_pointer_serializes_repo_location():
    pointer = ProviderEvidencePointer(
        provider="gitea",
        base_url="https://git.example.test",
        repo="team/backend",
        commit="abc123",
        path="src/main.py",
        line_start=10,
        line_end=12,
        content_hash="sha256:abc",
    )

    payload = pointer.to_dict()

    assert payload["provider"] == "gitea"
    assert payload["base_url"] == "https://git.example.test"
    assert payload["repo"] == "team/backend"
    assert payload["commit"] == "abc123"
    assert payload["line_start"] == 10
```

- [ ] **Step 2: Run targeted evidence tests**

Run:

```bash
python -m pytest tests/test_evidence_outputs.py -q
```

Expected: PASS if Task 1 already added `EvidencePointer`; if it fails, fix Task 1 before continuing.

- [ ] **Step 3: Preserve existing ask output and include provider fields when available**

Modify the `ask_project` evidence-building block in `whywiki/services/ask.py` so fact evidence keeps existing fields and passes through provider metadata:

```python
            provider_fields = {
                key: ev[0].get(key)
                for key in ("provider", "base_url", "repo", "ref", "commit", "line_start", "line_end", "content_hash")
                if ev and ev[0].get(key) is not None
            }
            evidence.append({"kind": "fact", "id": row["id"], "path": path, "score": score, **provider_fields})
```

Modify the block evidence branch so source/block answers keep the current local path behavior:

```python
            evidence.append({"kind": "block", "id": row["id"], "path": row["source_path"], "score": score})
```

- [ ] **Step 4: Run ask and evidence tests**

Run:

```bash
python -m pytest tests/test_evidence_outputs.py tests/test_basic_flow.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add whywiki/models.py whywiki/services/ask.py tests/test_evidence_outputs.py
git commit -m "feat: preserve provider evidence fields"
```

---

### Task 9: Review/Resolve Permission Gate

**Files:**
- Modify: `whywiki/app.py`
- Test: `tests/test_collaboration_api.py`

- [ ] **Step 1: Add failing conflict permission test**

Append to `tests/test_collaboration_api.py`:

```python
def test_conflict_status_without_workspace_keeps_current_local_behavior(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    project = client.post("/api/projects", json={"name": "Demo"}).json()
    build = client.post("/api/demo").json()
    conflicts = client.get(f"/api/projects/{build['project']['id']}/conflicts").json()

    if conflicts:
        response = client.patch(
            f"/api/projects/{build['project']['id']}/conflicts/{conflicts[0]['id']}",
            json={"status": "resolved"},
        )
        assert response.status_code == 200
```

Append a workspace-gated test:

```python
def test_conflict_status_rejects_when_workspace_write_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("WHYWIKI_COLLAB_STATIC_PERMISSIONS", "github:owner/whywiki-memory=read")
    client = TestClient(app)

    client.post("/api/workspace/connect", json={"provider": "github", "repo": "owner/whywiki-memory"})
    build = client.post("/api/demo").json()
    conflicts = client.get(f"/api/projects/{build['project']['id']}/conflicts").json()

    if conflicts:
        response = client.patch(
            f"/api/projects/{build['project']['id']}/conflicts/{conflicts[0]['id']}",
            json={"status": "resolved"},
        )
        assert response.status_code == 403
```

- [ ] **Step 2: Run tests to verify the gated test fails**

Run:

```bash
python -m pytest tests/test_collaboration_api.py -q
```

Expected: FAIL because conflict status updates are not gated when a workspace is configured.

- [ ] **Step 3: Add static permission registry helper for local tests**

Modify `whywiki/app.py` imports:

```python
import os

from .collaboration.providers import ProviderRegistry, StaticProviderClient
from .services.collaboration import CollaborationService
```

Add helper functions:

```python
def static_provider_registry_from_env() -> ProviderRegistry:
    registry = ProviderRegistry()
    raw = os.getenv("WHYWIKI_COLLAB_STATIC_PERMISSIONS", "")
    permissions: dict[str, tuple[bool, bool]] = {}
    for item in [part.strip() for part in raw.split(",") if part.strip()]:
        repo_key, value = item.split("=", 1)
        permissions[repo_key] = (value in {"read", "write"}, value == "write")
    if permissions:
        by_provider: dict[str, dict[str, tuple[bool, bool]]] = {}
        for repo_key, permission in permissions.items():
            provider_key = repo_key.split(":", 1)[0]
            if repo_key.startswith("gitea:"):
                provider_key = ":".join(repo_key.split(":")[:2])
            by_provider.setdefault(provider_key, {})[repo_key] = permission
        for provider_key, provider_permissions in by_provider.items():
            registry.register(provider_key, StaticProviderClient(provider_permissions))
    return registry


def collaboration_service_or_none() -> CollaborationService | None:
    paths = workspace_paths()
    if not paths.workspace_config_path.exists():
        return None
    return CollaborationService(load_workspace_config(paths), static_provider_registry_from_env())
```

- [ ] **Step 4: Gate conflict status updates when workspace is configured**

Modify `api_update_conflict` in `whywiki/app.py` before updating the row:

```python
    service = collaboration_service_or_none()
    if service is not None:
        try:
            service.require_review_access(project_slug=None)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
```

- [ ] **Step 5: Run collaboration API tests**

Run:

```bash
python -m pytest tests/test_collaboration_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Run existing API tests**

Run:

```bash
python -m pytest tests/test_api_surface.py tests/test_demo_flow.py tests/test_collaboration_api.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add whywiki/app.py tests/test_collaboration_api.py
git commit -m "feat: gate review actions by workspace permissions"
```

---

### Task 10: UI Permission And Account Status

**Files:**
- Modify: `whywiki/static/index.html`
- Modify: `whywiki/static/i18n.js`
- Modify: `whywiki/static/app.js`
- Modify: `whywiki/static/styles.css`
- Test: `tests/test_web_assets.py`

- [ ] **Step 1: Add failing web asset tests**

Append to `tests/test_web_assets.py`:

```python
from pathlib import Path


def test_collaboration_status_elements_exist():
    root = Path(__file__).resolve().parents[1] / "whywiki" / "static"
    html = (root / "index.html").read_text(encoding="utf-8")

    assert 'id="accountStatus"' in html
    assert 'id="workspaceStatus"' in html
    assert 'id="linkedRepoStatus"' in html


def test_collaboration_i18n_strings_exist():
    root = Path(__file__).resolve().parents[1] / "whywiki" / "static"
    i18n = (root / "i18n.js").read_text(encoding="utf-8")

    assert "Login with GitHub" in i18n
    assert "Login with Gitea" in i18n
    assert "缺少代码仓库访问权限" in i18n
```

- [ ] **Step 2: Run web asset tests to verify they fail**

Run:

```bash
python -m pytest tests/test_web_assets.py -q
```

Expected: FAIL because collaboration status elements and i18n strings do not exist.

- [ ] **Step 3: Add status containers to HTML**

Modify `whywiki/static/index.html` in the dashboard/sidebar account area:

```html
<section class="collaboration-panel" aria-label="Collaboration">
  <div class="collaboration-panel__row">
    <span data-i18n="accountStatusLabel">Accounts</span>
    <span id="accountStatus" class="status-pill">Not connected</span>
  </div>
  <div class="collaboration-panel__actions">
    <button id="loginGithubButton" class="secondary-action" type="button" data-i18n="loginGithub">Login with GitHub</button>
    <button id="loginGiteaButton" class="secondary-action" type="button" data-i18n="loginGitea">Login with Gitea</button>
  </div>
  <div class="collaboration-panel__row">
    <span data-i18n="workspaceStatusLabel">Workspace</span>
    <span id="workspaceStatus" class="status-pill">Not configured</span>
  </div>
  <div id="linkedRepoStatus" class="linked-repo-status"></div>
</section>
```

- [ ] **Step 4: Add i18n strings**

Modify `whywiki/static/i18n.js` in both language maps:

```javascript
accountStatusLabel: "Accounts",
workspaceStatusLabel: "Workspace",
loginGithub: "Login with GitHub",
loginGitea: "Login with Gitea",
notConnected: "Not connected",
notConfigured: "Not configured",
workspaceReady: "Workspace ready",
missingLinkedRepoAccess: "Missing linked repo access",
```

Chinese strings:

```javascript
accountStatusLabel: "账号",
workspaceStatusLabel: "工作区",
loginGithub: "使用 GitHub 登录",
loginGitea: "使用 Gitea 登录",
notConnected: "未连接",
notConfigured: "未配置",
workspaceReady: "工作区可用",
missingLinkedRepoAccess: "缺少代码仓库访问权限",
```

- [ ] **Step 5: Render account and workspace status**

Modify `whywiki/static/app.js` by adding:

```javascript
async function loadCollaborationStatus() {
  const [accounts, workspace] = await Promise.all([
    apiGet("/api/auth/accounts"),
    apiGet("/api/workspace/status")
  ]);
  renderAccountStatus(accounts.connected_accounts || []);
  renderWorkspaceStatus(workspace);
}

function renderAccountStatus(accounts) {
  const target = document.getElementById("accountStatus");
  if (!target) return;
  if (!accounts.length) {
    target.textContent = t("notConnected");
    target.className = "status-pill status-pill--muted";
    return;
  }
  target.textContent = accounts.map((account) => `${account.provider}:${account.account}`).join(", ");
  target.className = "status-pill status-pill--ok";
}

function renderWorkspaceStatus(workspace) {
  const target = document.getElementById("workspaceStatus");
  const linked = document.getElementById("linkedRepoStatus");
  if (!target || !linked) return;
  if (!workspace.configured) {
    target.textContent = t("notConfigured");
    target.className = "status-pill status-pill--muted";
    linked.textContent = "";
    return;
  }
  target.textContent = workspace.workspace.repo;
  target.className = "status-pill status-pill--ok";
  linked.textContent = "";
}
```

Call `loadCollaborationStatus()` during app initialization after the existing initial data load.

- [ ] **Step 6: Add compact styles**

Modify `whywiki/static/styles.css`:

```css
.collaboration-panel {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--border);
}

.collaboration-panel__row,
.collaboration-panel__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.secondary-action {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 6px;
  padding: 6px 8px;
  font: inherit;
}

.status-pill {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 12px;
  border: 1px solid var(--border);
}

.status-pill--ok {
  color: #166534;
  background: #dcfce7;
  border-color: #86efac;
}

.status-pill--muted {
  color: var(--muted);
  background: var(--surface-subtle);
}

.linked-repo-status {
  font-size: 12px;
  color: var(--muted);
}
```

- [ ] **Step 7: Run web tests**

Run:

```bash
python -m pytest tests/test_web_assets.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add whywiki/static/index.html whywiki/static/i18n.js whywiki/static/app.js whywiki/static/styles.css tests/test_web_assets.py
git commit -m "feat: show collaboration status in ui"
```

---

### Task 11: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/FEATURE_STATUS.md`

- [ ] **Step 1: Update README collaboration section**

Add a concise collaboration section to `README.md`:

```markdown
## Collaboration Model

WhyWiki uses Git providers for collaboration. A WhyWiki workspace is associated with a GitHub or Gitea repository that stores project-memory artifacts, while linked code repositories stay on their original providers.

- `whywiki.db` is a local rebuildable cache and should not be committed.
- The WhyWiki workspace repo stores configuration, facts, conflicts, review events, wiki pages, handover output, and pinned evidence-backed answers.
- Linked code repositories are referenced by provider, repo, commit, path, and range. WhyWiki does not copy code repositories into the workspace repo.
- Reading the workspace repo allows entering the workspace.
- Writing the workspace repo allows approving facts and resolving conflicts.
- Reading linked source repos allows source-backed evidence and rebuilds.
```

- [ ] **Step 2: Update feature status**

If `docs/FEATURE_STATUS.md` exists, add:

```markdown
## Git Provider Collaboration

Status: planned foundation implemented in local APIs and CLI.

Implemented surface:

- workspace artifact schema
- local connected-account metadata
- provider permission abstraction
- workspace read/write access reports
- linked repo access reports
- collaboration API and CLI status surfaces

Not included in this slice:

- source repo write actions
- pull request creation
- hosted storage
- enterprise role management
```

- [ ] **Step 3: Run focused collaboration tests**

Run:

```bash
python -m pytest \
  tests/test_collaboration_models.py \
  tests/test_workspace_artifacts.py \
  tests/test_provider_accounts.py \
  tests/test_provider_permissions.py \
  tests/test_collaboration_access.py \
  tests/test_collaboration_api.py \
  tests/test_collaboration_cli.py \
  -q
```

Expected: PASS.

- [ ] **Step 4: Run full verification**

Run:

```bash
python -m compileall whywiki
python -m pytest -q
```

Expected: PASS. If socket binding tests are blocked by the sandbox, rerun the same `python -m pytest -q` command outside the sandbox with approval and record the successful result.

- [ ] **Step 5: Inspect Git status**

Run:

```bash
git status --short --branch
```

Expected: only intended collaboration files are modified, plus any unrelated pre-existing local changes that were present before this plan started.

- [ ] **Step 6: Commit docs and final integration**

```bash
git add README.md docs/FEATURE_STATUS.md
git commit -m "docs: describe git provider collaboration"
```

---

## Self-Review

Spec coverage:

- Workspace repo as permission domain: Tasks 1, 2, 5, 6, and 7.
- `whywiki.db` as local rebuildable cache: Tasks 2 and 11.
- No code repo copies in the workspace repo: Tasks 2 and 11.
- GitHub and Gitea identities, including Gitea `base_url`: Tasks 1, 3, 4, 6, 7, and 10.
- Multiple provider accounts: Task 3.
- Workspace read and write permission gates: Tasks 4, 5, 6, 7, and 9.
- Linked source repo access checks: Tasks 1, 4, and 5.
- Evidence pointer provider/repo/commit/path/range shape: Tasks 1 and 8.
- Review and resolve permission model: Tasks 5 and 9.
- UI and CLI surfaces: Tasks 6, 7, and 10.
- Security defaults: Tasks 2, 3, 4, 5, 8, 9, and 11.

Placeholder scan:

- No unresolved placeholder markers.
- No empty implementation steps.
- Each code-changing task includes file paths, code snippets, targeted test commands, full verification commands where useful, and a commit step.

Type consistency:

- `RepoRef`, `LinkedRepo`, `ProviderIdentity`, `RepoPermission`, `WorkspaceConfig`, `WorkspaceAccessReport`, `EvidencePointer`, and `ReviewEvent` are introduced in Task 1 and reused by later tasks.
- `WorkspaceArtifactPaths`, `save_workspace_config`, and `load_workspace_config` are introduced in Task 2 and reused by API/CLI tasks.
- `ProviderRegistry` and `StaticProviderClient` are introduced in Task 4 and reused by the access service and permission-gated API tests.
