import shutil
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
            ["git", "-C", str(self.repo_path), "worktree", "remove", "--force", str(self.worktree_path)],
            capture_output=True,
            text=True,
        )


def create_workspace(repo_path: str) -> Workspace:
    repo = Path(repo_path).resolve()
    run_id = uuid.uuid4().hex[:12]
    runs_dir = repo / ".looping-louie" / "runs"
    worktree_path = runs_dir / run_id

    runs_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree_path), "HEAD"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return Workspace(run_id=run_id, repo_path=repo, worktree_path=worktree_path)