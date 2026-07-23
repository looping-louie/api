"""Controller for single-task execution."""

import uuid

from src.app.schemas.task import (
    ContinueRequest,
    ContinueResponse,
    GetResponse,
    StartRequest,
    StartResponse,
)
from src.app.services.execution_planner import create_execution_plan
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibrary,
)
from src.app.services.harness.decision import build_generator_base_prompt
from src.app.services.harness.reviewers import build_failed_feedback, run_single_reviewer
from src.app.services.instructions import build_assignment_instructions
from src.app.services.instructions import combine_generator_prompt
from src.app.services.llm_service.together import call_together
from src.app.services.model_context import build_reviewer_input
from src.app.services.task_checkpoint import (
    build_execution_run_path,
    parse_file_operations,
)
from src.app.utils.io import write_json
from . import utils


_TASK_RUNS = utils.TASK_RUNS


async def start_task(
    req: StartRequest,
    *,
    instruction_library: ExecutionInstructionLibrary,
) -> StartResponse:
    """Start a checkpoint-based task run and return first action."""
    run_id = uuid.uuid4().hex[:12]
    task = req.task.model_dump()

    if task['status'] != 'pending':
        return StartResponse(
            ok=False,
            run_id=run_id,
            iteration=0,
            status='stopped',
            next_action='none',
            continuation_token=None,
            token_revision=0,
            message='Task status must be pending to start stepped execution.',
            recoverable=False,
        )

    state = utils.TaskRunState(
        run_id=run_id,
        task_id=task['id'],
        task_prompt=task['prompt'],
        task_commit_message=task['commit_message'],
        constitution=req.constitution,
        project_profile=req.project_profile.model_dump(),
        generator_model=req.generator_model,
        reviewer_model=req.reviewer_model,
        planner_model=req.planner_model,
        required_reviewer_skills=list(req.required_reviewer_skills),
        generator_persona=req.generator_persona,
        instruction_library=instruction_library,
        run_path=build_execution_run_path(run_id),
        max_iterations=req.max_iterations,
        continuation_token=utils.new_continuation_token(),
        message='Run started. Provide workspace snapshot for iteration 1.',
    )

    write_json(
        state.run_path,
        'request.json',
        {
            'repo_path': req.repo_path,
            'task_id': task['id'],
            'prompt': task['prompt'],
            'constitution': req.constitution,
            'max_iterations': req.max_iterations,
            'generator_model': req.generator_model,
            'reviewer_model': req.reviewer_model,
        },
    )
    write_json(
        state.run_path,
        'instructions-snapshot.json',
        instruction_library.snapshot(),
    )

    _TASK_RUNS[run_id] = state

    return StartResponse(**utils.checkpoint_payload(state))


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
        return ContinueResponse(**utils.checkpoint_payload(state))

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

    await utils.apply_transition(
        state,
        req.action_result,
        create_execution_plan_fn=create_execution_plan,
        parse_file_operations_fn=parse_file_operations,
        build_generator_base_prompt_fn=build_generator_base_prompt,
        build_assignment_instructions_fn=build_assignment_instructions,
        combine_generator_prompt_fn=combine_generator_prompt,
        call_together_fn=call_together,
        build_reviewer_input_fn=build_reviewer_input,
        run_single_reviewer_fn=run_single_reviewer,
        build_failed_feedback_fn=build_failed_feedback,
    )

    response = ContinueResponse(**utils.checkpoint_payload(state))
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

    return GetResponse(**utils.checkpoint_payload(state))


__all__ = [
    'continue_task',
    'get_task',
    'start_task',
]
