"""
Workflow controller.

This is the highest-level orchestration entry point in Looping Louie.

Executes an entire development workflow defined in a tasks.json file.

Each pending task is processed sequentially by invoking the standard
single-task harness. Successfully reviewed changes are committed before
moving on to the next task.

Execution stops immediately when a task cannot be approved, ensuring the
repository never progresses beyond a failed step.
"""

from src.app.schemas import (
    RunHarnessRequest,
    RunHarnessResult,
    RunWorkflowRequest,
    RunWorkflowResponse,
)
from src.app.services.execution_planner import create_execution_plan
from src.app.services.git import commit_all, has_changes
from src.app.services.harness.adapters import build_local_harness_execution_ports
from src.app.services.harness.runner import build_execution_run_path, run_harness
from src.app.services.instructions import build_assignment_instructions
from src.app.services.workspace import cleanup_workspace, create_workspace
from src.app.services.task_plan import (
    get_next_pending_task,
    mark_task_done,
)
from src.app.utils.io import write_json


async def run_workflow(req: RunWorkflowRequest) -> RunWorkflowResponse:
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
        workspace = create_workspace(req.repo_path)
        run_path = build_execution_run_path(workspace.run_id)

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
                workspace=workspace,
                run_path=run_path,
                generator_instructions=generator_instructions,
                execution_ports=execution_ports,
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
            return RunWorkflowResponse(
                ok=False,
                status='stopped',
                task_id=task['id'],
                run_id=run_harness_result.run_id,
                approved=False,
                message=(
                    'Stopped because reviewers did not approve within '
                    'max_iterations.'
                ),
                completed=completed,
            )

        elif not has_changes(req.repo_path):
            return RunWorkflowResponse(
                ok=False,
                status='stopped',
                task_id=task['id'],
                run_id=run_harness_result.run_id,
                approved=True,
                message=(
                    'Run approved but no repository changes were found '
                    'to commit.'
                ),
                completed=completed,
            )

        else:
            # TODO:
            # Support configurable commit strategies.
            # Future options may include squash commits, signed commits,
            # conventional commits or disabling automatic commits entirely.
            commit_sha = commit_all(
                repo_path=req.repo_path,
                message=task['commit_message'],
            )

            mark_task_done(tasks, task['id'], run_harness_result.run_id)

            completed.append(
                {
                    'task_id': task['id'],
                    'run_id': run_harness_result.run_id,
                    'commit_sha': commit_sha,
                    'commit_message': task['commit_message'],
                    'phase': execution_plan.phase,
                    'reasoning': execution_plan.reasoning,
                    'generator': execution_plan.generator.model_dump(),
                    'reviewers': [
                        reviewer.model_dump()
                        for reviewer in execution_plan.reviewers
                    ],
                }
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
