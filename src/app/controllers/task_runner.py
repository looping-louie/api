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

from src.app.controllers.harness_runner import run_harness
from src.app.schemas import RunHarnessRequest, RunTasksRequest
from src.app.services.execution_planner_service import create_execution_plan
from src.app.services.git_service import commit_all, has_changes
from src.app.services.project_config_service import load_constitution
from src.app.services.project_profile_service import build_project_profile
from src.app.services.task_plan_service import (
    get_next_pending_task,
    load_tasks,
    mark_task_done,
    save_tasks,
)


async def run_tasks(req: RunTasksRequest) -> dict:
    """
    Execute every pending task from a tasks.json file.

    Workflow:

    1. Load the task list.
    2. Pick the first pending task.
    3. Build a task-specific execution plan.
    4. Execute the standard harness.
    5. If approved:
      - commit repository changes
      - mark the task as done
      - continue with the next task
    6. If rejected:
      - stop immediately
      - return the failing task and run identifier.

    Returns a summary of every completed task during this execution.
    """
    completed = []

    constitution = load_constitution(req.repo_path)
    project_profile = build_project_profile(req.repo_path)

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

        execution_plan = await create_execution_plan(
            model=req.planner_model,
            task_prompt=task["prompt"],
            project_profile=project_profile,
            constitution=constitution,
            required_skills=req.required_reviewer_skills,
            generator_persona=req.generator_persona,
        )

        run_response = await run_harness(
            RunHarnessRequest(
                repo_path=req.repo_path,
                prompt=task["prompt"],
                max_iterations=req.max_iterations,
                generator_model=req.generator_model,
                reviewer_model=req.reviewer_model,
                execution_plan=execution_plan,
                constitution=constitution,
            )
        )

        if not run_response.approved:
            return {
                "ok": False,
                "status": "stopped",
                "task_id": task["id"],
                "run_id": run_response.run_id,
                "approved": False,
                "message": (
                    "Stopped because reviewers did not approve within "
                    "max_iterations."
                ),
                "completed": completed,
            }

        if not has_changes(req.repo_path):
            return {
                "ok": False,
                "status": "stopped",
                "task_id": task["id"],
                "run_id": run_response.run_id,
                "approved": True,
                "message": (
                    "Run approved but no repository changes were found "
                    "to commit."
                ),
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
                "phase": execution_plan.phase,
                "reasoning": execution_plan.reasoning,
                "generator": execution_plan.generator.model_dump(),
                "reviewers": [
                    reviewer.model_dump()
                    for reviewer in execution_plan.reviewers
                ],
            }
        )
