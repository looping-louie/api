"""Controller for single-task execution."""

import uuid

from src.app.schemas import (
    RunHarnessRequest,
    RunHarnessResult,
)
from src.app.schemas.task import (
    RunRequest as RunTaskRequest,
    RunResponse as RunTaskResponse
)
from src.app.schemas.workflow import CompletedTask
from src.app.services.execution_planner import create_execution_plan
from src.app.services.harness.adapters import build_local_harness_execution_ports
from src.app.services.instructions import build_assignment_instructions
from src.app.services.harness.runner import build_execution_run_path, run_harness
from src.app.services.workspace import cleanup_workspace, create_workspace
from src.app.utils.io import write_json


async def run_task(req: RunTaskRequest) -> RunTaskResponse:
    """Execute one task using the same flow used by workflow execution."""
    task = req.task.model_dump()

    if task['status'] != 'pending':
        return RunTaskResponse(
            ok=False,
            status='stopped',
            commit_allowed=False,
            task_id=task['id'],
            message='Task status must be pending to run.',
        )

    constitution = req.constitution
    project_profile = req.project_profile.model_dump()

    execution_plan = await create_execution_plan(
        model=req.planner_model,
        task_prompt=task['prompt'],
        project_profile=project_profile,
        constitution=constitution,
        required_skills=req.required_reviewer_skills,
        generator_persona=req.generator_persona,
    )

    generator_instructions = build_assignment_instructions(
        role='generator',
        persona_id=execution_plan.generator.persona,
        skill_ids=execution_plan.generator.skills,
        focus=execution_plan.generator.focus,
    )

    execution_ports = build_local_harness_execution_ports()
    run_id = uuid.uuid4().hex[:12]
    workspace = create_workspace(req.repo_path, run_id)
    run_path = build_execution_run_path(run_id)

    write_json(
        run_path,
        'request.json',
        {
            'repo_path': req.repo_path,
            'prompt': task['prompt'],
            'constitution': constitution,
            'max_iterations': req.max_iterations,
            'generator_model': req.generator_model,
            'reviewer_model': req.reviewer_model,
        },
    )
    write_json(
        run_path,
        'execution-plan.json',
        execution_plan.model_dump(),
    )

    try:
        run_harness_result: RunHarnessResult = await run_harness(
            RunHarnessRequest(
                repo_path=req.repo_path,
                prompt=task['prompt'],
                max_iterations=req.max_iterations,
                generator_model=req.generator_model,
                reviewer_model=req.reviewer_model,
                execution_plan=execution_plan,
                constitution=constitution,
            ),
            run_id=run_id,
            workspace=workspace,
            run_path=run_path,
            generator_instructions=generator_instructions,
            execution_ports=execution_ports,
        )

        write_json(
            run_path,
            'response.json',
            run_harness_result.model_dump(),
        )
        write_json(
            run_path,
            'trace.json',
            [
                item.model_dump()
                for item in run_harness_result.execution_trace
            ],
        )
        write_json(
            run_path,
            'metrics.json',
            run_harness_result.run_metrics.model_dump(),
        )

        if run_harness_result.approved and run_harness_result.final_output:
            _validate_and_apply_final_diff(
                repo_path=req.repo_path,
                final_diff=run_harness_result.final_output,
                execution_ports=execution_ports,
            )
    finally:
        cleanup_workspace(workspace)

    # RunHarness Outcome Evaluation

    if not run_harness_result.approved:
        return RunTaskResponse(
            ok=False,
            status='stopped',
            commit_allowed=False,
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=False,
            message=(
                'Stopped because reviewers did not approve within '
                'max_iterations.'
            ),
        )

    else:
        return RunTaskResponse(
            ok=True,
            status='completed',
            commit_allowed=True,
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=True,
            message='Task approved. Commit must be executed by CLI.',
            completed=CompletedTask(
                task_id=task['id'],
                run_id=run_harness_result.run_id,
                commit_sha='deprecated API response field',
                commit_message='deprecated API response field',
                phase=execution_plan.phase,
                reasoning=execution_plan.reasoning,
                generator=execution_plan.generator,
                reviewers=execution_plan.reviewers,
            ),
        )


def _validate_and_apply_final_diff(
    *,
    repo_path: str,
    final_diff: str,
    execution_ports,
) -> None:
    """Apply an approved final diff to the original repository."""
    valid, error = execution_ports.git.validate_patch(
        repo_path,
        final_diff,
    )
    if not valid:
        raise RuntimeError(
            'Final diff does not apply to original repo: '
            f'{error}'
        )

    applied, error = execution_ports.git.apply_patch(
        repo_path,
        final_diff,
    )
    if not applied:
        raise RuntimeError(
            'Could not apply final diff to original repo: '
            f'{error}'
        )
