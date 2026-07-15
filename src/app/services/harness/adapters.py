"""Default local adapters for harness execution ports."""

from dataclasses import dataclass

from src.app.services.filesystem import apply_file_operations, parse_file_operations
from src.app.services.git import apply_patch, get_changed_files, get_git_diff, validate_patch
from src.app.services.harness.ports import HarnessExecutionPorts
from src.app.services.workspace import Workspace, cleanup_workspace, create_workspace


class LocalFileSystemAdapter:
    """Local file-operation adapter backed by the filesystem service."""

    def parse_file_operations(self, raw: str) -> list[dict]:
        return parse_file_operations(raw)

    def apply_file_operations(
        self,
        repo_path: str,
        operations: list[dict],
    ) -> None:
        apply_file_operations(repo_path, operations)


class LocalGitAdapter:
    """Local Git adapter backed by the git service."""

    def get_git_diff(self, repo_path: str) -> str:
        return get_git_diff(repo_path)

    def get_changed_files(self, repo_path: str) -> list[str]:
        return get_changed_files(repo_path)

    def validate_patch(
        self,
        repo_path: str,
        patch: str,
    ) -> tuple[bool, str]:
        return validate_patch(repo_path, patch)

    def apply_patch(
        self,
        repo_path: str,
        patch: str,
    ) -> tuple[bool, str]:
        return apply_patch(repo_path, patch)


class LocalWorkspaceAdapter:
    """Local workspace adapter backed by the workspace service."""

    def create_workspace(self, repo_path: str, run_id: str) -> Workspace:
        return create_workspace(repo_path, run_id)

    def cleanup_workspace(self, workspace: Workspace) -> None:
        cleanup_workspace(workspace)


@dataclass(frozen=True)
class LocalHarnessExecutionPorts(HarnessExecutionPorts):
    """Default harness execution ports using local in-process services."""


def build_local_harness_execution_ports() -> HarnessExecutionPorts:
    """Build local default execution ports used by current API runtime."""
    return LocalHarnessExecutionPorts(
        filesystem=LocalFileSystemAdapter(),
        git=LocalGitAdapter(),
        workspace=LocalWorkspaceAdapter(),
    )
