"""
Internal workspace model.

Defines the runtime information associated with one isolated harness
execution.

A workspace model only describes the execution environment. It does not
create directories, execute Git commands or manage its own lifecycle.
Those responsibilities belong to WorkspaceService.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    """
    Runtime workspace created for one harness execution.

    Attributes:
        run_id:
            Unique identifier assigned to the harness run.

        repo_path:
            Absolute path to the original user repository.

        run_path:
            Directory that contains the temporary detached worktree for this
            run under the target repository.

        worktree_path:
            Path to the temporary Git worktree where generated changes are
            applied and reviewed.

        source_commit_sha:
            Commit from which the isolated worktree was created.
    """

    run_id: str
    repo_path: Path
    run_path: Path
    worktree_path: Path
    source_commit_sha: str
