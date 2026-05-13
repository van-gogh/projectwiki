import pytest

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
    assert report.can_view_project_memory is False
    assert report.missing_required_linked_repo_access is True
    assert report.linked_repos[0].repo_key == "github:owner/code"


def test_optional_linked_repo_does_not_block_project_memory():
    config = WorkspaceConfig(
        workspace=RepoRef(provider="github", repo="owner/whywiki-memory"),
        projects={
            "demo": [
                LinkedRepo(id="optional-docs", repo=RepoRef(provider="github", repo="owner/docs"), required=False),
            ]
        },
    )
    registry = ProviderRegistry()
    registry.register(
        "github",
        StaticProviderClient(
            {
                "github:owner/whywiki-memory": (True, True),
                "github:owner/docs": (False, False),
            }
        ),
    )
    service = CollaborationService(config=config, providers=registry)

    report = service.check_workspace(project_slug="demo")

    assert report.linked_repos == ()
    assert report.missing_required_linked_repo_access is False
    assert report.can_view_project_memory is True


def test_require_workspace_read_raises_when_workspace_unreadable():
    config = WorkspaceConfig(workspace=RepoRef(provider="github", repo="owner/whywiki-memory"))
    registry = ProviderRegistry()
    registry.register("github", StaticProviderClient({"github:owner/whywiki-memory": (False, False)}))
    service = CollaborationService(config=config, providers=registry)

    with pytest.raises(PermissionError, match="cannot read this WhyWiki workspace repo"):
        service.require_workspace_read()


def test_require_review_access_raises_when_workspace_write_missing():
    config = WorkspaceConfig(workspace=RepoRef(provider="github", repo="owner/whywiki-memory"))
    registry = ProviderRegistry()
    registry.register("github", StaticProviderClient({"github:owner/whywiki-memory": (True, False)}))
    service = CollaborationService(config=config, providers=registry)

    with pytest.raises(PermissionError, match="cannot write this WhyWiki workspace repo"):
        service.require_review_access()


def test_require_review_access_raises_when_required_linked_repo_missing():
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

    with pytest.raises(PermissionError, match="cannot read all required linked source repos"):
        service.require_review_access(project_slug="demo")


def test_require_review_access_returns_report_when_all_permissions_exist():
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
                "github:owner/code": (True, False),
            }
        ),
    )
    service = CollaborationService(config=config, providers=registry)

    report = service.require_review_access(project_slug="demo")

    assert report.can_review is True
    assert report.can_view_project_memory is True

