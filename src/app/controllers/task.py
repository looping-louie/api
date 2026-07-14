"""Controller for single-task execution."""

from src.app.schemas import (
    RunHarnessRequest,
    RunHarnessResult,
)
from src.app.schemas.task import RunRequest as RunTaskRequest
from src.app.schemas.task import RunResponse as RunTaskResponse
from src.app.schemas.workflow import CompletedTask
from src.app.services.execution_planner import create_execution_plan
from src.app.services.git import commit_all, has_changes
from src.app.services.harness import run_harness
from src.app.services.project.project_config_service import load_constitution
from src.app.services.project.project_profile_service import build_project_profile


async def run_task(req: RunTaskRequest) -> RunTaskResponse:
    """Execute one task using the same flow used by workflow execution."""
    task = req.task.model_dump()

    if task['status'] != 'pending':
        return RunTaskResponse(
            ok=False,
            status='stopped',
            task_id=task['id'],
            message='Task status must be pending to run.',
        )

    constitution = load_constitution(req.repo_path)
    project_profile = build_project_profile(req.repo_path)

    execution_plan = await create_execution_plan(
        model=req.planner_model,
        task_prompt=task['prompt'],
        project_profile=project_profile,
        constitution=constitution,
        required_skills=req.required_reviewer_skills,
        generator_persona=req.generator_persona,
    )

    run_harness_result: RunHarnessResult = await run_harness(
        RunHarnessRequest(
            repo_path=req.repo_path,
            prompt=task['prompt'],
            max_iterations=req.max_iterations,
            generator_model=req.generator_model,
            reviewer_model=req.reviewer_model,
            execution_plan=execution_plan,
            constitution=constitution,
        )
    )

    if not run_harness_result.approved:
        return RunTaskResponse(
            ok=False,
            status='stopped',
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=False,
            message=(
                'Stopped because reviewers did not approve within '
                'max_iterations.'
            ),
        )

    if not has_changes(req.repo_path):
        return RunTaskResponse(
            ok=False,
            status='stopped',
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=True,
            message=(
                'Run approved but no repository changes were found '
                'to commit.'
            ),
        )

    commit_sha = commit_all(
        repo_path=req.repo_path,
        message=task['commit_message'],
    )

    return RunTaskResponse(
        ok=True,
        status='completed',
        task_id=task['id'],
        run_id=run_harness_result.run_id,
        approved=True,
        message='Task completed and committed.',
        completed=CompletedTask(
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            commit_sha=commit_sha,
            commit_message=task['commit_message'],
            phase=execution_plan.phase,
            reasoning=execution_plan.reasoning,
            generator=execution_plan.generator,
            reviewers=execution_plan.reviewers,
        ),
    )
