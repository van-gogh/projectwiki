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
