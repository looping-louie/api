"""Private state and helper functions for task controllers."""

from dataclasses import dataclass, field
from pathlib import Path
import uuid
from typing import Any, cast

from src.app.schemas import (
    ExecutionPlan,
    RunHarnessRequest,
)
from src.app.schemas.task import (
    CompletedTask,
    ContinueResponse,
    TaskAction,
    TaskErrorCode,
    TaskStatus,
)
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibrary,
)
from src.app.utils.io import write_json


@dataclass
class _TaskRunState:
    """In-memory state for checkpoint-based task execution."""

    run_id: str
    task_id: str
    task_prompt: str
    task_commit_message: str
    constitution: str
    project_profile: dict[str, Any]
    generator_model: str
    reviewer_model: str
    planner_model: str
    required_reviewer_skills: list[str]
    generator_persona: str | None
    instruction_library: ExecutionInstructionLibrary
    run_path: Path
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
    latest_repo_context: str | None = None
    latest_final_diff: str | None = None
    latest_changed_file_count: int = 0
    latest_generator_output: str = ''
    latest_reviewer_feedback: str = ''
    latest_generator_metrics: dict[str, Any] | None = None
    pending_operations: list[dict[str, Any]] = field(default_factory=list)
    execution_plan: ExecutionPlan | None = None
    generator_instructions: str | None = None
    idempotency_cache: dict[tuple[str | None, str], ContinueResponse] = field(
        default_factory=dict
    )


_TASK_RUNS: dict[str, _TaskRunState] = {}


def _checkpoint_payload(state: _TaskRunState) -> dict[str, Any]:
    """Build checkpoint response payload from in-memory task run state."""
    payload = None

    if state.next_action == 'apply_operations':
        payload = {
            'apply_operations': {
                'operations': state.pending_operations,
                'generator_metrics': state.latest_generator_metrics,
            },
            'meta': {
                'iteration': state.iteration,
                'task_id': state.task_id,
            },
        }

    return {
        'ok': state.error_code is None,
        'run_id': state.run_id,
        'iteration': state.iteration,
        'status': state.status,
        'next_action': state.next_action,
        'continuation_token': state.continuation_token,
        'token_revision': state.token_revision,
        'payload': payload,
        'commit_allowed': state.commit_allowed,
        'completed': state.completed,
        'error_code': state.error_code,
        'message': state.message,
        'recoverable': state.recoverable,
    }


async def _apply_transition(
    state: _TaskRunState,
    action_result: Any,
    *,
    create_execution_plan_fn: Any,
    parse_file_operations_fn: Any,
    build_generator_base_prompt_fn: Any,
    build_assignment_instructions_fn: Any,
    combine_generator_prompt_fn: Any,
    call_together_fn: Any,
    build_reviewer_input_fn: Any,
    run_single_reviewer_fn: Any,
    build_failed_feedback_fn: Any,
) -> None:
    """Advance one checkpoint transition after validating action alignment."""
    state.error_code = None
    state.recoverable = None

    if action_result.action == 'collect_snapshot':
        await _handle_collect_snapshot(
            state,
            action_result,
            create_execution_plan_fn=create_execution_plan_fn,
            parse_file_operations_fn=parse_file_operations_fn,
            build_generator_base_prompt_fn=build_generator_base_prompt_fn,
            build_assignment_instructions_fn=build_assignment_instructions_fn,
            combine_generator_prompt_fn=combine_generator_prompt_fn,
            call_together_fn=call_together_fn,
        )
        return

    if action_result.action == 'apply_operations':
        _handle_apply_operations(state, action_result)
        return

    if action_result.action == 'submit_review_input':
        await _handle_submit_review_input(
            state,
            action_result,
            build_reviewer_input_fn=build_reviewer_input_fn,
            run_single_reviewer_fn=run_single_reviewer_fn,
            build_failed_feedback_fn=build_failed_feedback_fn,
        )
        return

    if action_result.action == 'commit_if_allowed':
        _handle_commit_if_allowed(state, action_result)
        return


async def _handle_collect_snapshot(
    state: _TaskRunState,
    action_result: Any,
    *,
    create_execution_plan_fn: Any,
    parse_file_operations_fn: Any,
    build_generator_base_prompt_fn: Any,
    build_assignment_instructions_fn: Any,
    combine_generator_prompt_fn: Any,
    call_together_fn: Any,
) -> None:
    """Handle collect_snapshot continuation and move run to apply_operations."""
    state.latest_repo_context = action_result.repo_context

    try:
        if state.execution_plan is None:
            state.execution_plan = await create_execution_plan_fn(
                model=state.planner_model,
                task_prompt=state.task_prompt,
                project_profile=state.project_profile,
                constitution=state.constitution,
                required_skills=[
                    state.instruction_library.normalize_skill_id(
                        skill_id
                    )
                    for skill_id in state.required_reviewer_skills
                ],
                generator_persona=(
                    state.instruction_library.normalize_persona_id(
                        state.generator_persona
                    )
                    if state.generator_persona is not None
                    else None
                ),
                skill_registry=(
                    state.instruction_library.skill_registry()
                ),
                persona_registry=(
                    state.instruction_library.persona_registry()
                ),
            )
            created_execution_plan = state.execution_plan
            if created_execution_plan is None:
                raise RuntimeError('Planner did not return an execution plan.')
            state.generator_instructions = build_assignment_instructions_fn(
                role='generator',
                persona_content=(
                    state.instruction_library.persona_content(
                        created_execution_plan.generator.persona
                    )
                ),
                skill_contents=(
                    state.instruction_library.skill_contents(
                        created_execution_plan.generator.skills
                    )
                ),
                focus=created_execution_plan.generator.focus,
            )
            write_json(
                state.run_path,
                'execution-plan.json',
                created_execution_plan.model_dump(),
            )

        execution_plan = state.execution_plan
        if execution_plan is None:
            raise RuntimeError('Execution plan must be available before generation.')

        prompt_context = build_generator_base_prompt_fn(
            iteration=state.iteration,
            repo_context=state.latest_repo_context or '',
            req=RunHarnessRequest(
                prompt=state.task_prompt,
                repo_path='checkpoint-run',
                max_iterations=state.max_iterations,
                generator_model=state.generator_model,
                reviewer_model=state.reviewer_model,
                execution_plan=execution_plan,
                constitution=state.constitution,
            ),
            previous_generator_output=state.latest_generator_output,
            reviewer_feedback=state.latest_reviewer_feedback,
        )
        current_prompt = combine_generator_prompt_fn(
            assignment_instructions=state.generator_instructions or '',
            task_prompt=prompt_context,
        )
        generator_response = await call_together_fn(
            state.generator_model,
            current_prompt,
        )
        operations = cast(
            list[dict[str, Any]],
            parse_file_operations_fn(
                generator_response['text']
            ),
        )

        state.pending_operations = operations
        state.latest_generator_output = generator_response['text']
        state.latest_generator_metrics = {
            'model': state.generator_model,
            'input_tokens': generator_response.get('input_tokens', 0),
            'output_tokens': generator_response.get('output_tokens', 0),
            'duration_ms': generator_response.get('duration_ms', 0),
        }
        write_json(
            state.run_path,
            f'generator/iteration-{state.iteration}-response.json',
            generator_response,
        )
        write_json(
            state.run_path,
            f'generator/iteration-{state.iteration}-operations.json',
            {'operations': operations},
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        state.pending_operations = []
        state.latest_generator_metrics = {
            'model': state.generator_model,
            'input_tokens': 0,
            'output_tokens': 0,
            'duration_ms': 0,
        }
        _close_state(
            state,
            status='failed',
            message=(
                'Generator/operations step failed during collect_snapshot: '
                f'{exc}'
            ),
        )
        return

    _advance_state(
        state,
        next_action='apply_operations',
        message=(
            f'Iteration {state.iteration} snapshot received. '
            'Apply proposed operations locally and continue.'
        ),
    )


def _handle_apply_operations(state: _TaskRunState, action_result: Any) -> None:
    """Handle apply_operations continuation and route to review or retry."""
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


async def _handle_submit_review_input(
    state: _TaskRunState,
    action_result: Any,
    *,
    build_reviewer_input_fn: Any,
    run_single_reviewer_fn: Any,
    build_failed_feedback_fn: Any,
) -> None:
    """Handle submit_review_input continuation and route to commit or retry."""
    state.latest_final_diff = action_result.final_diff
    state.latest_changed_file_count = len(action_result.changed_file_contents)

    if state.execution_plan is None:
        _close_state(
            state,
            status='failed',
            message='Execution plan is missing for reviewer decision step.',
        )
        return

    changed_contents = _format_changed_file_contents(
        action_result.changed_file_contents
    )
    review_input = build_reviewer_input_fn(
        user_prompt=state.task_prompt,
        final_diff=action_result.final_diff,
        changed_file_contents=changed_contents,
    )

    req = RunHarnessRequest(
        prompt=state.task_prompt,
        repo_path='checkpoint-run',
        max_iterations=state.max_iterations,
        generator_model=state.generator_model,
        reviewer_model=state.reviewer_model,
        execution_plan=state.execution_plan,
        constitution=state.constitution,
    )

    reviewer_results = []

    for index, assignment in enumerate(state.execution_plan.reviewers, start=1):
        result = await run_single_reviewer_fn(
            req=req,
            assignment=assignment,
            reviewer_index=index,
            phase=state.execution_plan.phase,
            review_input=review_input,
            iteration=state.iteration,
            run_id=state.run_id,
            run_path=state.run_path,
            instruction_library=state.instruction_library,
        )
        reviewer_results.append(result)

    state.latest_reviewer_feedback = build_failed_feedback_fn(reviewer_results)
    approved = all(result.approved for result in reviewer_results)
    write_json(
        state.run_path,
        f'reviewers/iteration-{state.iteration}-summary.json',
        {
            'approved': approved,
            'reviewer_feedback': state.latest_reviewer_feedback,
            'reviewers': [
                reviewer.model_dump()
                for reviewer in reviewer_results
            ],
        },
    )

    if approved:
        state.commit_allowed = True
        state.completed = CompletedTask(
            task_id=state.task_id,
            run_id=state.run_id,
            commit_sha='deprecated API response field',
            commit_message='deprecated API response field',
            phase=state.execution_plan.phase,
            reasoning=state.execution_plan.reasoning,
            generator=state.execution_plan.generator,
            reviewers=state.execution_plan.reviewers,
        )
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


def _handle_commit_if_allowed(state: _TaskRunState, action_result: Any) -> None:
    """Handle commit_if_allowed continuation and close run in terminal state."""
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


def _format_changed_file_contents(changed_file_contents: dict[str, str]) -> str:
    """Render changed file content map into reviewer prompt text."""
    if not changed_file_contents:
        return ''

    blocks = []
    for path, content in changed_file_contents.items():
        blocks.append(
            f'### FILE: {path}\n\n{content}'
        )

    return '\n\n'.join(blocks)


# Package-internal symbols used by controllers/task/__init__.py.
TASK_RUNS = _TASK_RUNS
TaskRunState = _TaskRunState
checkpoint_payload = _checkpoint_payload
apply_transition = _apply_transition
new_continuation_token = _new_continuation_token
