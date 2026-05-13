from __future__ import annotations

from whywiki.collaboration.models import WorkspaceAccessReport, WorkspaceConfig
from whywiki.collaboration.providers import ProviderRegistry


class CollaborationService:
    def __init__(self, config: WorkspaceConfig, providers: ProviderRegistry):
        self.config = config
        self.providers = providers

    def check_workspace(self, project_slug: str | None) -> WorkspaceAccessReport:
        workspace_permission = self.providers.check_repo(self.config.workspace)
        if not workspace_permission.can_read:
            return WorkspaceAccessReport(workspace=workspace_permission)
        linked_permissions = []
        if project_slug is not None:
            for linked_repo in self.config.projects.get(project_slug, []):
                if not linked_repo.required:
                    continue
                permission = self.providers.check_repo(linked_repo.repo)
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
