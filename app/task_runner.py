"""
Task runner.

This is the highest-level orchestration entry point in Looping Louie.

Executes an entire development backlog defined in a tasks.json file.

Each pending task is processed sequentially by invoking the standard
single-task harness. Successfully reviewed changes are committed before
moving on to the next task.

Execution stops immediately when a task cannot be approved, ensuring the
repository never progresses beyond a failed step.
"""

from pydantic import BaseModel, Field

from app.git_ops import commit_all, has_changes
from app.runner import run_harness
from app.schemas import RunRequest
from app.task_file import (
    get_next_pending_task,
    load_tasks,
    mark_task_done,
    save_tasks,
)


# TODO:
# Allow individual tasks to override execution settings such as
# models, skills and max_iterations.
class RunTasksRequest(BaseModel):
    """
    Request model for the /run-tasks endpoint.

    Defines the repository, task file and default execution parameters that
    will be used for every pending task unless future task-level overrides
    are introduced.
    """
    repo_path: str
    tasks_path: str
    max_iterations: int = 3
    generator_model: str = "deepseek-ai/DeepSeek-V4-Pro"
    reviewer_model: str = "gpt-4.1-mini"
    skills: list[str] = Field(default_factory=lambda: ["small_patch_quality"])


async def run_tasks(req: RunTasksRequest) -> dict:
    """
    Execute every pending task from a tasks.json file.

    Workflow:

    1. Load the task list.
    2. Pick the first pending task.
    3. Execute the standard harness.
    4. If approved:
      - commit repository changes
      - mark the task as done
      - continue with the next task
    5. If rejected:
      - stop immediately
      - return the failing task and run identifier.

    Returns a summary of every completed task during this execution.
    """
    completed = []

    # TODO:
    # Resume interrupted executions automatically.
    # Since completed tasks are persisted, execution can continue from the
    # first pending task after a crash or restart.
    while True:
        tasks = load_tasks(req.tasks_path)
        task = get_next_pending_task(tasks)

        if task is None:
            return {
                "ok": True,
                "status": "completed",
                "completed": completed,
            }

        run_response = await run_harness(
            RunRequest(
                repo_path=req.repo_path,
                prompt=task["prompt"],
                max_iterations=req.max_iterations,
                generator_model=req.generator_model,
                reviewer_model=req.reviewer_model,
                skills=req.skills,
            )
        )

        if not run_response.approved:
            return {
                "ok": False,
                "status": "stopped",
                "task_id": task["id"],
                "run_id": run_response.run_id,
                "approved": False,
                "message": "Stopped because reviewers did not approve within max_iterations.",
                "completed": completed,
            }

        if not has_changes(req.repo_path):
            return {
                "ok": False,
                "status": "stopped",
                "task_id": task["id"],
                "run_id": run_response.run_id,
                "approved": True,
                "message": "Run approved but no repository changes were found to commit.",
                "completed": completed,
            }

        # TODO:
        # Support configurable commit strategies.
        # Future options may include squash commits, signed commits,
        # conventional commits or disabling automatic commits entirely.
        commit_sha = commit_all(
            repo_path=req.repo_path,
            message=task["commit_message"],
        )

        tasks = load_tasks(req.tasks_path)
        mark_task_done(tasks, task["id"], run_response.run_id)
        save_tasks(req.tasks_path, tasks)

        completed.append(
            {
                "task_id": task["id"],
                "run_id": run_response.run_id,
                "commit_sha": commit_sha,
                "commit_message": task["commit_message"],
            }
        )