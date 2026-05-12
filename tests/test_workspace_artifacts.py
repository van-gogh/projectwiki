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
