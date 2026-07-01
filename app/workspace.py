import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Workspace:
    run_id: str
    repo_path: Path
    worktree_path: Path

    def cleanup(self) -> None:
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo_path),
                "worktree",
                "remove",
                "--force",
                str(self.worktree_path),
            ],
            capture_output=True,
            text=True,
        )


def assert_git_repo(repo: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"{repo} is not a Git repository.")


def prune_worktrees(repo: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "prune"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def assert_clean_repo(repo: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    if result.stdout.strip():
        raise RuntimeError(
            "Repo has uncommitted changes. Commit or stash before running Looping Louie."
        )


def create_workspace(repo_path: str) -> Workspace:
    repo = Path(repo_path).resolve()

    if not repo.exists():
        raise RuntimeError(f"Repository does not exist: {repo}")

    if not repo.is_dir():
        raise RuntimeError(f"Repository path is not a directory: {repo}")

    assert_git_repo(repo)
    prune_worktrees(repo)
    assert_clean_repo(repo)

    run_id = uuid.uuid4().hex[:12]

    runs_dir = repo / ".looping-louie" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    worktree_path = runs_dir / run_id

    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "--detach",
            str(worktree_path),
            "HEAD",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return Workspace(
        run_id=run_id,
        repo_path=repo,
        worktree_path=worktree_path,
    )