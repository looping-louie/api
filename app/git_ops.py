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