"""
Workspace lifecycle service.

Creates and removes the isolated execution environments used by the harness.

Each harness run receives:

- a unique run identifier;
- a run-scoped directory under the repository for worktree internals;
- a detached Git worktree created from the current repository HEAD.

This service coordinates filesystem setup and workspace lifecycle policy.
It delegates all Git-specific operations to git_service.

Removing a workspace deletes its temporary worktree but preserves the run
directory under the repository.
"""

from pathlib import Path

from src.app.models.workspace import Workspace
from src.app.services.git import (
    assert_git_repo,
    assert_clean_repo,
    create_worktree,
    get_head_sha,
    prune_worktrees,
    remove_worktree)


def create_workspace(repo_path: str | Path, run_id: str) -> Workspace:
    """
    Create an isolated workspace for one harness execution.

    The original repository must exist, be a Git repository and contain no
    uncommitted changes.

    A detached worktree is created from the current HEAD commit under:

        .looping-louie/runs/{run_id}/worktree

    Args:
        repo_path:
            Path to the original user repository.
        run_id:
            Stable caller-assigned run identifier used for run paths.

    Returns:
        The newly created Workspace.

    Raises:
        RuntimeError:
            If the repository path is invalid, the repository is not clean or
            the Git worktree cannot be created.
    """
    repo = _resolve_repository_path(repo_path)

    assert_git_repo(repo)
    prune_worktrees(repo)
    assert_clean_repo(repo)

    source_commit_sha = get_head_sha(repo)

    run_path = repo / ".looping-louie" / "runs" / run_id
    worktree_path = run_path / "worktree"

    run_path.mkdir(parents=True, exist_ok=False)

    try:
        create_worktree(
            repo_path=repo,
            worktree_path=worktree_path,
            source_ref=source_commit_sha,
        )
    except Exception:
        # Remove the run directory only if worktree creation failed before
        # the workspace could be fully initialized.
        try:
            run_path.rmdir()
        except OSError:
            pass

        raise

    return Workspace(
        repo_path=repo,
        run_path=run_path,
        worktree_path=worktree_path,
        source_commit_sha=source_commit_sha,
    )


def cleanup_workspace(workspace: Workspace) -> None:
    """
    Remove the temporary Git worktree associated with a workspace.

    The run directory is deliberately preserved so repository-scoped
    workspace data can be inspected after execution.

    Args:
        workspace:
            Workspace whose temporary worktree should be removed.

    Raises:
        RuntimeError:
            If Git cannot remove the worktree.
    """
    remove_worktree(
        repo_path=workspace.repo_path,
        worktree_path=workspace.worktree_path,
        force=True,
    )


def _resolve_repository_path(repo_path: str | Path) -> Path:
    """
    Resolve and validate a repository filesystem path.

    This validation concerns the filesystem path itself. Git-specific
    validation is delegated to git_service.
    """
    repo = Path(repo_path).expanduser().resolve()

    if not repo.exists():
        raise RuntimeError(f"Repository does not exist: {repo}")

    if not repo.is_dir():
        raise RuntimeError(f"Repository path is not a directory: {repo}")

    return repo
