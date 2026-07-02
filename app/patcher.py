"""
Git patch and diff helpers.

The generator no longer produces git patches directly. Instead, file
operations are applied to a worktree and Git is used to produce the real
diff.

This module is still responsible for:
- extracting diffs from a worktree;
- listing changed files;
- validating the final diff;
- applying approved diffs back to the original repository.
"""

import subprocess
from pathlib import Path


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