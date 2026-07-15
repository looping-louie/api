"""Controller for single-task execution."""

from dataclasses import dataclass, field
import uuid
from typing import Any

from src.app.schemas import (
    RunHarnessRequest,
    RunHarnessResult,
)
from src.app.schemas.task import (
    ContinueRequest,
    ContinueResponse,
    GetResponse,
    StartRequest,
    StartResponse,
    TaskAction,
    TaskErrorCode,
    TaskStatus,
    RunRequest as RunTaskRequest,
    RunResponse as RunTaskResponse,
)
from src.app.schemas.workflow import CompletedTask
from src.app.services.execution_planner import create_execution_plan
from src.app.services.harness.adapters import build_local_harness_execution_ports
from src.app.services.instructions import build_assignment_instructions
from src.app.services.harness.runner import build_execution_run_path, run_harness
from src.app.services.workspace import cleanup_workspace, create_workspace
from src.app.utils.io import write_json


@dataclass
class _TaskRunState:
    """In-memory state for checkpoint-based task execution."""

    run_id: str
    task_id: str
    max_iterations: int
    iteration: int = 1
    status: TaskStatus = 'in_progress'
    next_action: TaskAction = 'collect_snapshot'
    token_revision: int = 1
    continuation_token: str | None = None
    commit_allowed: bool = False
    completed: CompletedTask | None = None
    message: str | None = None
    recoverable: bool | None = None
    error_code: TaskErrorCode | None = None
    idempotency_cache: dict[tuple[str | None, str], ContinueResponse] = field(
        default_factory=dict
    )


_TASK_RUNS: dict[str, _TaskRunState] = {}


async def start_task(req: StartRequest) -> StartResponse:
    """Start a checkpoint-based task run and return first action."""
    run_id = uuid.uuid4().hex[:12]
    task = req.task.model_dump()

    state = _TaskRunState(
        run_id=run_id,
        task_id=task['id'],
        max_iterations=req.max_iterations,
        continuation_token=_new_continuation_token(),
        message='Run started. Provide workspace snapshot for iteration 1.',
    )

    _TASK_RUNS[run_id] = state

    return StartResponse(**_checkpoint_payload(state))


async def continue_task(req: ContinueRequest) -> ContinueResponse:
    """Advance one checkpoint transition for a started task run."""
    state = _TASK_RUNS.get(req.run_id)

    if state is None:
        return ContinueResponse(
            ok=False,
            run_id=req.run_id,
            iteration=0,
            status='failed',
            next_action='none',
            continuation_token=None,
            token_revision=0,
            error_code='run_not_found',
            message='Run was not found.',
            recoverable=False,
        )

    if state.status != 'in_progress':
        return ContinueResponse(**_checkpoint_payload(state))

    cache_key = (req.continuation_token, req.idempotency_key)
    cached = state.idempotency_cache.get(cache_key)

    if cached is not None:
        return cached.model_copy(deep=True)

    if req.continuation_token != state.continuation_token:
        response = ContinueResponse(
            ok=False,
            run_id=state.run_id,
            iteration=state.iteration,
            status='failed',
            next_action=state.next_action,
            continuation_token=state.continuation_token,
            token_revision=state.token_revision,
            error_code='token_conflict',
            message='Continuation token does not match current run state.',
            recoverable=True,
        )
        state.idempotency_cache[cache_key] = response.model_copy(deep=True)
        return response

    if req.action_result.action != state.next_action:
        response = ContinueResponse(
            ok=False,
            run_id=state.run_id,
            iteration=state.iteration,
            status='failed',
            next_action=state.next_action,
            continuation_token=state.continuation_token,
            token_revision=state.token_revision,
            error_code='invalid_transition',
            message='Action does not match next_action for this run state.',
            recoverable=True,
        )
        state.idempotency_cache[cache_key] = response.model_copy(deep=True)
        return response

    _apply_transition(state, req.action_result)

    response = ContinueResponse(**_checkpoint_payload(state))
    state.idempotency_cache[cache_key] = response.model_copy(deep=True)

    return response


async def get_task(run_id: str) -> GetResponse:
    """Return latest checkpoint state for one run identifier."""
    state = _TASK_RUNS.get(run_id)

    if state is None:
        return GetResponse(
            ok=False,
            run_id=run_id,
            iteration=0,
            status='failed',
            next_action='none',
            continuation_token=None,
            token_revision=0,
            error_code='run_not_found',
            message='Run was not found.',
            recoverable=False,
        )

    return GetResponse(**_checkpoint_payload(state))


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


def _checkpoint_payload(state: _TaskRunState) -> dict[str, Any]:
    """Build checkpoint response payload from in-memory task run state."""
    return {
        'ok': state.error_code is None,
        'run_id': state.run_id,
        'iteration': state.iteration,
        'status': state.status,
        'next_action': state.next_action,
        'continuation_token': state.continuation_token,
        'token_revision': state.token_revision,
        'payload': None,
        'commit_allowed': state.commit_allowed,
        'completed': state.completed,
        'error_code': state.error_code,
        'message': state.message,
        'recoverable': state.recoverable,
    }


def _apply_transition(state: _TaskRunState, action_result: Any) -> None:
    """Advance one checkpoint transition after validating action alignment."""
    state.error_code = None
    state.recoverable = None

    if action_result.action == 'collect_snapshot':
        _advance_state(
            state,
            next_action='apply_operations',
            message=(
                f'Iteration {state.iteration} snapshot received. '
                'Apply proposed operations locally and continue.'
            ),
        )
        return

    if action_result.action == 'apply_operations':
        if action_result.applied:
            _advance_state(
                state,
                next_action='submit_review_input',
                message='Operations applied. Submit review input for this iteration.',
            )
            return

        if state.iteration >= state.max_iterations:
            _close_state(
                state,
                status='stopped',
                message='Stopped because apply_operations failed at max_iterations.',
            )
            return

        state.iteration += 1
        _advance_state(
            state,
            next_action='collect_snapshot',
            message='Operation apply failed. Proceeding to next iteration snapshot.',
        )
        return

    if action_result.action == 'submit_review_input':
        approved = bool(action_result.final_diff.strip())

        if approved:
            state.commit_allowed = True
            _advance_state(
                state,
                next_action='commit_if_allowed',
                message='Review approved. Commit changes locally and continue.',
            )
            return

        if state.iteration >= state.max_iterations:
            _close_state(
                state,
                status='stopped',
                message='Stopped because reviewers did not approve within max_iterations.',
            )
            return

        state.iteration += 1
        _advance_state(
            state,
            next_action='collect_snapshot',
            message='Review not approved. Proceeding to next iteration snapshot.',
        )
        return

    if action_result.action == 'commit_if_allowed':
        state.commit_allowed = False

        if action_result.committed:
            _close_state(
                state,
                status='completed',
                message='Task completed and commit acknowledged by CLI.',
            )
            return

        _close_state(
            state,
            status='stopped',
            message='Task approved but commit was not completed by CLI.',
        )
        return


def _advance_state(
    state: _TaskRunState,
    *,
    next_action: TaskAction,
    message: str,
) -> None:
    """Advance to a new in-progress action with fresh continuation token."""
    state.status = 'in_progress'
    state.next_action = next_action
    state.message = message
    state.token_revision += 1
    state.continuation_token = _new_continuation_token()


def _close_state(
    state: _TaskRunState,
    *,
    status: TaskStatus,
    message: str,
) -> None:
    """Close a run in terminal status and invalidate continuation token."""
    state.status = status
    state.next_action = 'none'
    state.message = message
    state.token_revision += 1
    state.continuation_token = None


def _new_continuation_token() -> str:
    """Generate opaque token used to protect continuation ordering."""
    return uuid.uuid4().hex
