"""Execution ports used by the harness orchestration workflow."""

from dataclasses import dataclass
from typing import Protocol

from src.app.models.workspace import Workspace


class FileSystemPort(Protocol):
    """Contract for file-operation parsing and application."""

    def parse_file_operations(self, raw: str) -> list[dict]:
        """Parse and validate generator output into file operations."""

    def apply_file_operations(
        self,
        repo_path: str,
        operations: list[dict],
    ) -> None:
        """Apply validated file operations to a repository path."""


class GitPort(Protocol):
    """Contract for Git operations used by harness execution."""

    def get_git_diff(self, repo_path: str) -> str:
        """Return repository diff against HEAD."""

    def get_changed_files(self, repo_path: str) -> list[str]:
        """Return changed file paths against HEAD."""

    def validate_patch(
        self,
        repo_path: str,
        patch: str,
    ) -> tuple[bool, str]:
        """Validate that a patch can be applied."""

    def apply_patch(
        self,
        repo_path: str,
        patch: str,
    ) -> tuple[bool, str]:
        """Apply a patch to a repository."""


class WorkspacePort(Protocol):
    """Contract for isolated workspace lifecycle management."""

    def create_workspace(self, repo_path: str, run_id: str) -> Workspace:
        """Create a workspace for one harness execution."""

    def cleanup_workspace(self, workspace: Workspace) -> None:
        """Clean up temporary workspace resources."""


@dataclass(frozen=True)
class HarnessExecutionPorts:
    """Execution dependencies required by the harness runner."""

    filesystem: FileSystemPort
    git: GitPort
    workspace: WorkspacePort
