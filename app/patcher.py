import subprocess
from pathlib import Path


def validate_patch(repo_path: str, patch: str) -> tuple[bool, str]:
    return _git_apply(repo_path, patch, check_only=True)


def apply_patch(repo_path: str, patch: str) -> tuple[bool, str]:
    return _git_apply(repo_path, patch, check_only=False)


def get_git_diff(repo_path: str) -> str:
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