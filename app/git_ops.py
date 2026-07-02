import subprocess
from pathlib import Path


def has_changes(repo_path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", repo_path, "status", "--porcelain"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return bool(result.stdout.strip())


def commit_all(repo_path: str, message: str) -> str:
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


def get_head_sha(repo_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()