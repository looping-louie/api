"""Controller for resuming a single-task execution."""

from collections.abc import Awaitable, Callable
from typing import Any

from src.app.schemas.task import ContinueRequest, ContinueResponse
from src.app.services.execution_planner import create_execution_plan
from src.app.services.harness.decision import build_generator_base_prompt
from src.app.services.harness.reviewers import (
    build_failed_feedback,
    run_single_reviewer,
)
from src.app.services.instructions import (
    build_assignment_instructions,
    combine_generator_prompt,
)
from src.app.services.llm_service.together import call_together
from src.app.services.model_context import build_reviewer_input
from src.app.services.task_checkpoint import parse_file_operations

from . import utils


async def resume_task(
    req: ContinueRequest,
    *,
    create_execution_plan_fn: Callable[..., Awaitable[Any]] = (
        create_execution_plan
    ),
    call_together_fn: Callable[..., Awaitable[Any]] = call_together,
) -> ContinueResponse:
    """Advance one checkpoint transition for a started task run."""
    state = utils.TASK_RUNS.get(req.run_id)
    if state is None:
        return ContinueResponse(
            ok=False,
            run_id=req.run_id,
            iteration=0,
            status="failed",
            next_action="none",
            continuation_token=None,
            token_revision=0,
            error_code="run_not_found",
            message="Run was not found.",
            recoverable=False,
        )
    if state.status != "in_progress":
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
            status="failed",
            next_action=state.next_action,
            continuation_token=state.continuation_token,
            token_revision=state.token_revision,
            error_code="token_conflict",
            message="Continuation token does not match current run state.",
            recoverable=True,
        )
        state.idempotency_cache[cache_key] = response.model_copy(deep=True)
        return response

    if req.action_result.action != state.next_action:
        response = ContinueResponse(
            ok=False,
            run_id=state.run_id,
            iteration=state.iteration,
            status="failed",
            next_action=state.next_action,
            continuation_token=state.continuation_token,
            token_revision=state.token_revision,
            error_code="invalid_transition",
            message="Action does not match next_action for this run state.",
            recoverable=True,
        )
        state.idempotency_cache[cache_key] = response.model_copy(deep=True)
        return response

    await utils.apply_transition(
        state,
        req.action_result,
        create_execution_plan_fn=create_execution_plan_fn,
        parse_file_operations_fn=parse_file_operations,
        build_generator_base_prompt_fn=build_generator_base_prompt,
        build_assignment_instructions_fn=build_assignment_instructions,
        combine_generator_prompt_fn=combine_generator_prompt,
        call_together_fn=call_together_fn,
        build_reviewer_input_fn=build_reviewer_input,
        run_single_reviewer_fn=run_single_reviewer,
        build_failed_feedback_fn=build_failed_feedback,
    )
    response = ContinueResponse(**utils.checkpoint_payload(state))
    state.idempotency_cache[cache_key] = response.model_copy(deep=True)
    return response
