"""
Workflow controller.

This is the highest-level orchestration entry point in Looping Louie.

Executes one pending workflow task per call.

The endpoint returns commit handoff metadata so the CLI can perform the local
commit operation before invoking /workflow/run again for the next pending task.
"""

import uuid

from src.app.schemas import (
    RunHarnessRequest,
    RunHarnessResult,
    RunWorkflowRequest,
    RunWorkflowResponse,
)
from src.app.schemas.workflow import CompletedTask
from src.app.services.execution_planner import create_execution_plan
from src.app.services.harness.adapters import build_local_harness_execution_ports
from src.app.services.harness.runner import build_execution_run_path, run_harness
from src.app.services.instructions import build_assignment_instructions
from src.app.services.workspace import cleanup_workspace, create_workspace
from src.app.services.task_plan import (
    get_next_pending_task,
    mark_task_done,
)
from src.app.utils.io import write_json
from .utils import validate_and_apply_final_diff


async def run_workflow(req: RunWorkflowRequest) -> RunWorkflowResponse:
    """
    Execute one pending workflow task and return commit handoff data.

        Returns:
        - approved task metadata with commit_allowed=True, or
        - stopped state with commit_allowed=False.
    """
    completed = []

    tasks = [task.model_dump() for task in req.tasks]

    constitution = req.constitution
    project_profile = req.project_profile.model_dump()

    # TODO:
    # Resume interrupted executions automatically.
    # Since completed tasks are persisted, execution can continue from the
    # first pending task after a crash or restart.
    while True:
        task = get_next_pending_task(tasks)

        if task is None:
            return RunWorkflowResponse(
                ok=True,
                status='completed',
                commit_allowed=False,
                completed=completed,
            )

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
                validate_and_apply_final_diff(
                    repo_path=req.repo_path,
                    final_diff=run_harness_result.final_output,
                    execution_ports=execution_ports,
                )
        finally:
            cleanup_workspace(workspace)

        # RunHarness Outcome Evaluation

        if not run_harness_result.approved:
            return RunWorkflowResponse(
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
                completed=completed,
            )

        mark_task_done(tasks, task['id'], run_harness_result.run_id)

        completed_task = CompletedTask(
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            commit_sha='deprecated API response field',
            commit_message='deprecated API response field',
            phase=execution_plan.phase,
            reasoning=execution_plan.reasoning,
            generator=execution_plan.generator,
            reviewers=execution_plan.reviewers,
        )
        completed.append(completed_task)

        return RunWorkflowResponse(
            ok=True,
            status='completed',
            commit_allowed=True,
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=True,
            message=(
                'Task approved. Commit must be executed by CLI before '
                'continuing workflow.'
            ),
            completed=completed,
        )


__all__ = ['run_workflow']
