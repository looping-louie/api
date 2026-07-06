"""
Git repository operations.

Provides the minimal Git functionality required by the task runner.

Responsibilities include:
- detecting pending repository changes;
- creating commits for approved tasks;
- retrieving commit identifiers.

This module intentionally contains only repository-level operations.
Worktree management and patch generation live in separate modules.
"""

import subprocess
from pathlib import Path


def has_changes(repo_path: str) -> bool:
    """
    Return whether the repository contains uncommitted changes.
    """
    result = subprocess.run(
        ["git", "-C", repo_path, "status", "--porcelain"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return bool(result.stdout.strip())

# TODO:
# Support alternative commit strategies such as:
# - signed commits
# - conventional commits
# - squash commits
# - disabled automatic commits

# TODO:
# Stage only files modified by the current task instead of `git add .`.
# This will prevent unrelated local changes from accidentally entering
# an automated task commit.
def commit_all(repo_path: str, message: str) -> str:
    """
    Commit every pending repository change.

    Returns the SHA of the newly created commit.
    """
    repo = Path(repo_path).resolve()

    add = subprocess.run(
        ["git", "-C", str(repo), "add", "."],
        capture_output=True,
        text=True,
    )

    if add.returncode != 0:
        raise RuntimeError(add.stderr.strip())

    commit = subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", message],
        capture_output=True,
        text=True,
    )

    if commit.returncode != 0:
        raise RuntimeError(commit.stderr.strip())

    return get_head_sha(str(repo))


# TODO:
# Expose additional repository metadata (branch, base commit, dirty state)
# for execution reports and future dashboards.
def get_head_sha(repo_path: str) -> str:
    """
    Return the SHA of the current HEAD commit.
    """
    result = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def validate_patch(repo_path: str, patch: str) -> tuple[bool, str]:
    """
    Check whether a patch can be applied cleanly without modifying files.
    """
    return _git_apply(repo_path, patch, check_only=True)


def apply_patch(repo_path: str, patch: str) -> tuple[bool, str]:
    """
    Apply a validated patch to a repository.
    """
    return _git_apply(repo_path, patch, check_only=False)

# TODO:
# Rename this module. Since the generator now emits file operations
# instead of patches, this file is really git_diff.py or git_ops_diff.py.
def get_git_diff(repo_path: str) -> str:
    """
    Return the current git diff for a repository.

    Uses `git add -N` first so newly created untracked files appear in the
    diff without staging their contents.
    """
    subprocess.run(
        ["git", "add", "-N", "."],
        cwd=Path(repo_path),
        text=True,
        capture_output=True,
    )

    result = subprocess.run(
        ["git", "diff"],
        cwd=Path(repo_path),
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout


def get_changed_files(repo_path: str) -> list[str]:
    """
    Return the list of files changed in the current working tree.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=Path(repo_path),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _git_apply(repo_path: str, patch: str, check_only: bool) -> tuple[bool, str]:
    """
    Run git apply in either validation or mutation mode.
    """
    command = ["git", "apply"]
    if check_only:
        command.append("--check")

    result = subprocess.run(
        command,
        cwd=Path(repo_path),
        input=patch,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        return False, result.stderr.strip()

    return True, result.stdout.strip()