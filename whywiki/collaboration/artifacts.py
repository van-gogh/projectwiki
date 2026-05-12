from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from whywiki.collaboration.jsonio import append_jsonl, read_json, write_json
from whywiki.collaboration.models import ReviewEvent, WorkspaceConfig


@dataclass(frozen=True)
class WorkspaceArtifactPaths:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root))

    @property
    def workspace_config_path(self) -> Path:
        return self.root / "whywiki.yaml"

    @property
    def projects_dir(self) -> Path:
        return self.root / "projects"


def _safe_project_dir(paths: WorkspaceArtifactPaths, project_slug: str) -> Path:
    slug_path = Path(project_slug)
    if (
        not project_slug
        or project_slug in {".", ".."}
        or slug_path.is_absolute()
        or "/" in project_slug
        or "\\" in project_slug
    ):
        raise ValueError("project_slug must be a single non-empty path segment")

    projects_dir = paths.projects_dir.resolve()
    project_dir = (paths.projects_dir / project_slug).resolve()
    if project_dir != projects_dir and projects_dir not in project_dir.parents:
        raise ValueError("project_slug must stay inside the workspace projects directory")
    return project_dir


def workspace_project_dir(paths: WorkspaceArtifactPaths, project_slug: str) -> Path:
    project_dir = _safe_project_dir(paths, project_slug)
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "wiki").mkdir(exist_ok=True)
    (project_dir / "ask").mkdir(exist_ok=True)
    return project_dir


def save_workspace_config(paths: WorkspaceArtifactPaths, config: WorkspaceConfig) -> None:
    write_json(paths.workspace_config_path, {"workspace": config.workspace.to_dict()})
    for project_slug, linked_repos in config.projects.items():
        project_dir = workspace_project_dir(paths, project_slug)
        write_json(
            project_dir / "linked-repos.yaml",
            {"linked_repos": [linked_repo.to_dict() for linked_repo in linked_repos]},
        )


def load_workspace_config(paths: WorkspaceArtifactPaths) -> WorkspaceConfig:
    workspace_payload = read_json(paths.workspace_config_path)
    projects: dict[str, dict[str, object]] = {}
    if paths.projects_dir.exists():
        for linked_repos_path in sorted(paths.projects_dir.glob("*/linked-repos.yaml")):
            projects[linked_repos_path.parent.name] = read_json(linked_repos_path)
    return WorkspaceConfig.from_dict(
        {
            "workspace": workspace_payload["workspace"],
            "projects": projects,
        }
    )


def save_review_event(paths: WorkspaceArtifactPaths, event: ReviewEvent) -> None:
    project_dir = workspace_project_dir(paths, event.project_slug)
    append_jsonl(project_dir / "review-events.jsonl", event.to_dict())
