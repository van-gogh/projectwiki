from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from whywiki.collaboration.models import (
    EvidencePointer,
    LinkedRepo,
    ProviderIdentity,
    RepoPermission,
    RepoRef,
    ReviewEvent,
    WorkspaceAccessReport,
    WorkspaceConfig,
)


def test_repo_ref_requires_gitea_base_url():
    ref = RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test")

    assert ref.provider == "gitea"
    assert ref.base_url == "https://git.example.test"
    assert ref.key == "gitea:https://git.example.test:team/backend"


def test_repo_ref_rejects_gitea_without_base_url():
    with pytest.raises(ValueError, match="base_url"):
        RepoRef(provider="gitea", repo="team/backend")


@pytest.mark.parametrize("base_url", ["git.example.test", "ftp://git.example.test", "https://"])
def test_repo_ref_rejects_invalid_gitea_base_url(base_url):
    with pytest.raises(ValueError, match="base_url"):
        RepoRef(provider="gitea", repo="team/backend", base_url=base_url)


def test_repo_ref_normalizes_gitea_base_url_trailing_slash():
    ref = RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test/")

    assert ref.base_url == "https://git.example.test"
    assert ref.provider_key == "gitea:https://git.example.test"


def test_repo_ref_normalizes_github_key_without_base_url():
    ref = RepoRef(provider="github", repo="owner/project")

    assert ref.base_url is None
    assert ref.key == "github:owner/project"


def test_repo_ref_clears_github_base_url():
    ref = RepoRef(provider="github", repo="owner/project", base_url="https://github.example.test")

    assert ref.base_url is None
    assert ref.provider_key == "github"
    assert ref.key == "github:owner/project"


def test_provider_identity_clears_github_base_url():
    identity = ProviderIdentity(
        provider="github",
        account="alice",
        provider_user_id="42",
        base_url="https://github.example.test",
    )

    assert identity.base_url is None
    assert identity.provider_key == "github"


@pytest.mark.parametrize("repo", ["owner", "owner/", "owner /repo", "owner/re po", "owner/repo/extra"])
def test_repo_ref_rejects_invalid_repo(repo):
    with pytest.raises(ValueError, match="owner/name"):
        RepoRef(provider="github", repo=repo)


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

    assert payload["projects"]["demo"]["linked_repos"] == [
        {
            "id": "backend",
            "provider": "gitea",
            "repo": "team/backend",
            "base_url": "https://git.example.test",
            "branch": "main",
            "required": True,
        }
    ]
    assert restored.workspace.repo == "owner/whywiki-memory"
    assert restored.projects["demo"][0].id == "backend"
    assert restored.projects["demo"][0].required is True


def test_linked_repo_uses_flat_serialization_shape():
    linked_repo = LinkedRepo(
        id="backend",
        repo=RepoRef(provider="gitea", repo="team/backend", base_url="https://git.example.test/"),
    )

    payload = linked_repo.to_dict()
    restored = LinkedRepo.from_dict(payload)

    assert payload == {
        "id": "backend",
        "provider": "gitea",
        "repo": "team/backend",
        "base_url": "https://git.example.test",
        "branch": "main",
        "required": True,
    }
    assert restored.id == "backend"
    assert restored.repo.key == "gitea:https://git.example.test:team/backend"
    assert restored.branch == "main"
    assert restored.required is True


def test_workspace_config_from_dict_keeps_indexable_shape():
    config = WorkspaceConfig.from_dict(
        {
            "workspace": {"provider": "github", "repo": "owner/whywiki-memory"},
            "projects": {
                "demo": {
                    "linked_repos": [
                        {
                            "id": "backend",
                            "provider": "gitea",
                            "repo": "team/backend",
                            "base_url": "https://git.example.test/",
                        }
                    ]
                }
            },
        }
    )

    assert config.projects["demo"][0].branch == "main"
    assert config.to_dict()["projects"]["demo"]["linked_repos"][0]["base_url"] == "https://git.example.test"


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


def test_provider_identity_from_dict_round_trip():
    restored = ProviderIdentity.from_dict(
        {
            "provider": "gitea",
            "account": "alice",
            "provider_user_id": "42",
            "base_url": "https://git.example.test/",
        }
    )

    assert restored.to_dict() == {
        "provider": "gitea",
        "account": "alice",
        "provider_user_id": "42",
        "base_url": "https://git.example.test",
    }
    assert restored.provider_key == "gitea:https://git.example.test"


def test_provider_identity_rejects_invalid_gitea_base_url():
    with pytest.raises(ValueError, match="base_url"):
        ProviderIdentity(
            provider="gitea",
            account="alice",
            provider_user_id="42",
            base_url="git.example.test",
        )


def test_workspace_access_report_separates_workspace_and_linked_repo_permissions():
    report = WorkspaceAccessReport(
        workspace=RepoPermission(repo_key="github:owner/whywiki-memory", can_read=True, can_write=True),
        linked_repos=[
            RepoPermission(repo_key="gitea:https://git.example.test:team/backend", can_read=False, can_write=False)
        ],
    )

    assert report.can_enter_workspace is True
    assert report.can_review is True
    assert report.can_view_project_memory is False
    assert report.missing_required_linked_repo_access is True
    assert report.missing_required_linked_repo_permissions[0].repo_key == "gitea:https://git.example.test:team/backend"
    assert report.to_dict()["can_enter_workspace"] is True
    assert report.to_dict()["can_review"] is True
    assert report.to_dict()["can_view_project_memory"] is False
    assert report.to_dict()["missing_required_linked_repo_access"] is True


def test_workspace_access_report_requires_workspace_write_for_review():
    read_only_report = WorkspaceAccessReport(
        workspace=RepoPermission(repo_key="github:owner/whywiki-memory", can_read=True, can_write=False)
    )
    write_without_read_report = WorkspaceAccessReport(
        workspace=RepoPermission(repo_key="github:owner/whywiki-memory", can_read=False, can_write=True)
    )

    assert read_only_report.can_enter_workspace is True
    assert read_only_report.can_review is False
    assert write_without_read_report.can_enter_workspace is False
    assert write_without_read_report.can_review is False
    assert write_without_read_report.missing_required_linked_repo_access is False


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


def test_evidence_pointer_omits_optional_none_fields():
    payload = EvidencePointer(
        provider="github",
        repo="owner/project",
        commit="abc123",
        path="src/app.py",
    ).to_dict()

    assert payload == {
        "provider": "github",
        "repo": "owner/project",
        "commit": "abc123",
        "path": "src/app.py",
    }
    assert "base_url" not in payload
    assert "ref" not in payload
    assert "line_start" not in payload


def test_review_event_to_dict_shape():
    event = ReviewEvent(
        id="rev_1",
        project_slug="demo",
        subject_type="fact",
        subject_id="fact_1",
        action="approve",
        actor=ProviderIdentity(provider="github", account="alice", provider_user_id="42"),
        created_at=datetime(2026, 5, 12, 10, 30, 0),
        note="checked",
    )

    assert event.to_dict() == {
        "id": "rev_1",
        "project_slug": "demo",
        "subject_type": "fact",
        "subject_id": "fact_1",
        "action": "approve",
        "actor": {
            "provider": "github",
            "account": "alice",
            "provider_user_id": "42",
        },
        "created_at": "2026-05-12T10:30:00",
        "note": "checked",
    }


def test_model_instances_are_frozen_after_construction():
    ref = RepoRef(provider="github", repo="owner/project")

    with pytest.raises(FrozenInstanceError):
        ref.repo = "owner/other"
