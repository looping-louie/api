"""
Git infrastructure service.

Provides the low-level Git operations required by the harness.

Responsibilities include:

- validating Git repositories and their working state;
- reading repository metadata;
- creating, pruning and removing temporary worktrees;
- detecting and listing repository changes;
- generating real Git diffs from filesystem modifications;
- validating and applying approved patches;
- creating commits for completed tasks.

This module is the only service that should execute Git commands directly.
Workspace lifecycle, model context construction and file-operation validation
belong to their respective services.
"""

import subprocess
from pathlib import Path


RepositoryPath = str | Path


def assert_git_repo(repo_path: RepositoryPath) -> None:
    """
    Ensure that the supplied path belongs to a Git working tree.

    Raises:
        RuntimeError:
            If Git cannot identify the path as part of a repository.
    """
    repo = _resolve_path(repo_path)

    result = _run_git(
        repo,
        "rev-parse",
        "--is-inside-work-tree",
    )

    if result.returncode != 0 or result.stdout.strip() != "true":
        raise RuntimeError(f"{repo} is not a Git repository.")


def assert_clean_repo(repo_path: RepositoryPath) -> None:
    """
    Ensure that a repository has no staged, unstaged or untracked changes.

    Looping Louie starts from a clean repository so every run has a stable
    source commit and produces deterministic diffs.

    Raises:
        RuntimeError:
            If Git cannot inspect the repository or pending changes exist.
    """
    if has_changes(repo_path):
        raise RuntimeError(
            "Repo has uncommitted changes. "
            "Commit or stash before running Looping Louie."
        )


def has_changes(repo_path: RepositoryPath) -> bool:
    """
    Return whether a repository contains pending changes.

    Staged, unstaged and untracked files are considered changes.
    """
    repo = _resolve_path(repo_path)

    result = _run_git(
        repo,
        "status",
        "--porcelain",
    )
    _require_success(result, "Could not inspect repository status")

    return bool(result.stdout.strip())


def get_head_sha(repo_path: RepositoryPath) -> str:
    """
    Return the full SHA of the current HEAD commit.
    """
    repo = _resolve_path(repo_path)

    result = _run_git(
        repo,
        "rev-parse",
        "HEAD",
    )
    _require_success(result, "Could not read repository HEAD")

    return result.stdout.strip()


def prune_worktrees(repo_path: RepositoryPath) -> None:
    """
    Remove stale Git worktree metadata left by previous executions.
    """
    repo = _resolve_path(repo_path)

    result = _run_git(
        repo,
        "worktree",
        "prune",
    )
    _require_success(result, "Could not prune Git worktrees")


def create_worktree(
    repo_path: RepositoryPath,
    worktree_path: RepositoryPath,
    source_ref: str = "HEAD",
) -> None:
    """
    Create a detached Git worktree from a repository reference.

    Args:
        repo_path:
            Main repository that owns the worktree.

        worktree_path:
            Filesystem path where the worktree will be created.

        source_ref:
            Commit, branch or other Git reference used as the worktree source.

    Raises:
        RuntimeError:
            If Git cannot create the worktree.
    """
    repo = _resolve_path(repo_path)
    worktree = _resolve_path(worktree_path)

    result = _run_git(
        repo,
        "worktree",
        "add",
        "--detach",
        str(worktree),
        source_ref,
    )
    _require_success(result, "Could not create Git worktree")


def remove_worktree(
    repo_path: RepositoryPath,
    worktree_path: RepositoryPath,
    *,
    force: bool = False,
) -> None:
    """
    Remove a Git worktree owned by a repository.

    Args:
        repo_path:
            Main repository that owns the worktree.

        worktree_path:
            Worktree path to remove.

        force:
            Whether Git should remove the worktree even when it contains
            pending changes.

    Raises:
        RuntimeError:
            If Git cannot remove the worktree.
    """
    repo = _resolve_path(repo_path)
    worktree = _resolve_path(worktree_path)

    command = ["worktree", "remove"]

    if force:
        command.append("--force")

    command.append(str(worktree))

    result = _run_git(repo, *command)
    _require_success(result, "Could not remove Git worktree")


# TODO:
# Support alternative commit strategies such as:
# - signed commits
# - conventional commits
# - squash commits
# - disabled automatic commits

# TODO:
# Stage only files modified by the current task instead of `git add --all`.
# This will prevent unrelated local changes from accidentally entering
# an automated task commit.
def commit_all(repo_path: RepositoryPath, message: str) -> str:
    """
    Stage and commit every pending repository change.

    Args:
        repo_path:
            Repository where the commit should be created.

        message:
            Commit message.

    Returns:
        SHA of the newly created commit.

    Raises:
        RuntimeError:
            If changes cannot be staged or committed.
    """
    repo = _resolve_path(repo_path)

    add_result = _run_git(
        repo,
        "add",
        "--all",
    )
    _require_success(add_result, "Could not stage repository changes")

    commit_result = _run_git(
        repo,
        "commit",
        "-m",
        message,
    )
    _require_success(commit_result, "Could not create Git commit")

    return get_head_sha(repo)


def get_git_diff(repo_path: RepositoryPath) -> str:
    """
    Return the current repository diff against HEAD.

    Newly created files are first registered with intent-to-add so Git includes
    them in the resulting diff without staging their contents.
    """
    repo = _resolve_path(repo_path)

    _make_untracked_files_visible_to_diff(repo)

    result = _run_git(
        repo,
        "diff",
        "--binary",
        "HEAD",
    )
    _require_success(result, "Could not generate Git diff")

    return result.stdout


def get_changed_files(repo_path: RepositoryPath) -> list[str]:
    """
    Return paths changed relative to HEAD.

    Includes modified, deleted and newly created files.
    """
    repo = _resolve_path(repo_path)

    _make_untracked_files_visible_to_diff(repo)

    result = _run_git(
        repo,
        "diff",
        "--name-only",
        "HEAD",
    )
    _require_success(result, "Could not list changed files")

    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def validate_patch(
    repo_path: RepositoryPath,
    patch: str,
) -> tuple[bool, str]:
    """
    Check whether a patch can be applied without modifying the repository.

    Returns:
        A tuple containing:

        - whether the patch is valid;
        - Git output or the validation error.
    """
    return _git_apply(repo_path, patch, check_only=True)


def apply_patch(
    repo_path: RepositoryPath,
    patch: str,
) -> tuple[bool, str]:
    """
    Apply a Git patch to a repository.

    Returns:
        A tuple containing:

        - whether the patch was applied successfully;
        - Git output or the application error.
    """
    return _git_apply(repo_path, patch, check_only=False)


def _make_untracked_files_visible_to_diff(repo_path: Path) -> None:
    """
    Register untracked files with intent-to-add.

    This changes the Git index metadata but does not stage file contents.
    It allows newly created files to appear in `git diff`.
    """
    result = _run_git(
        repo_path,
        "add",
        "-N",
        ".",
    )
    _require_success(
        result,
        "Could not register untracked files for diff generation",
    )


def _git_apply(
    repo_path: RepositoryPath,
    patch: str,
    *,
    check_only: bool,
) -> tuple[bool, str]:
    """
    Run `git apply` in validation or mutation mode.
    """
    repo = _resolve_path(repo_path)

    command = ["apply"]

    if check_only:
        command.append("--check")

    result = _run_git(
        repo,
        *command,
        input_text=patch,
    )

    if result.returncode != 0:
        return False, result.stderr.strip()

    return True, result.stdout.strip()


def _run_git(
    repo_path: Path,
    *arguments: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Execute a Git command against a repository.

    Error interpretation is deliberately left to the calling operation because
    some commands, such as patch validation, use non-zero return codes as part
    of their normal result.
    """
    return subprocess.run(
        ["git", "-C", str(repo_path), *arguments],
        input=input_text,
        capture_output=True,
        text=True,
    )


def _require_success(
    result: subprocess.CompletedProcess[str],
    fallback_message: str,
) -> None:
    """
    Raise RuntimeError when a Git command fails.
    """
    if result.returncode == 0:
        return

    detail = result.stderr.strip() or result.stdout.strip()

    if detail:
        raise RuntimeError(f"{fallback_message}: {detail}")

    raise RuntimeError(fallback_message)


def _resolve_path(path: RepositoryPath) -> Path:
    """
    Convert a string or Path into an absolute filesystem path.
    """
    return Path(path).expanduser().resolve()