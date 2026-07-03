"""
Workspace management.

Every harness execution runs inside an isolated Git worktree rather than
the original repository.

This guarantees that:

- rejected iterations never modify the user's repository;
- every run starts from a clean HEAD;
- prompts, diffs and logs are stored alongside the temporary worktree;
- approved changes can later be applied back to the original repository.

One workspace is created per harness run.
"""

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

# TODO:
# Record the source commit SHA associated with the workspace so every
# execution can be traced back to the exact repository revision.
@dataclass
class Workspace:
    """
    Represents the execution workspace for one harness run.

    A workspace owns both the temporary Git worktree and the directory where
    all prompts, responses, diffs and metrics are persisted.
    """

    run_id: str
    repo_path: Path
    run_path: Path
    worktree_path: Path

    # TODO:
    # Keep failed worktrees optionally for debugging instead of always
    # removing them. This would simplify reproducing generator failures.
    def cleanup(self) -> None:
        """
        Remove the temporary Git worktree created for this run.

        The original repository is never affected.
        """
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
    """
    Ensure the supplied path belongs to a Git repository.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"{repo} is not a Git repository.")


def prune_worktrees(repo: Path) -> None:
    """
    Remove stale Git worktree metadata left by previous executions.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "prune"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def assert_clean_repo(repo: Path) -> None:
    """
    Verify that the repository has no uncommitted changes.

    Looping Louie always starts from a clean repository to guarantee
    reproducible runs and deterministic diffs.
    """
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

# TODO:
# Support resuming existing workspaces for interrupted executions.
def create_workspace(repo_path: str) -> Workspace:
    """
    Create a fresh execution workspace.

    The workspace consists of:

    - a unique run identifier;
    - a run directory under .looping-louie/runs/;
    - a detached Git worktree checked out at HEAD.

    The returned Workspace object is used throughout the execution lifecycle.
    """
    repo = Path(repo_path).resolve()

    if not repo.exists():
        raise RuntimeError(f"Repository does not exist: {repo}")

    if not repo.is_dir():
        raise RuntimeError(f"Repository path is not a directory: {repo}")

    assert_git_repo(repo)
    prune_worktrees(repo)
    assert_clean_repo(repo)

    run_id = uuid.uuid4().hex[:12]

    run_path = repo / ".looping-louie" / "runs" / run_id
    worktree_path = run_path / "worktree"

    run_path.mkdir(parents=True, exist_ok=True)

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
        run_path=run_path,
        worktree_path=worktree_path,
    )