"""Main harness orchestration workflow."""

import asyncio
import time

from src.app.schemas import (
    ModelMetrics,
    ReviewerMetrics,
    ReviewerResult,
    RunHarnessRequest,
    RunHarnessResponse,
    RunMetrics,
)
from src.app.services.file_change import apply_file_operations, parse_file_operations
from src.app.services.git import apply_patch, get_changed_files, get_git_diff, validate_patch
from src.app.services.harness.context import build_repo_context
from src.app.services.harness.execution_plan import build_static_execution_plan
from src.app.services.harness.instructions import (
    build_assignment_instructions,
    combine_generator_prompt,
)
from src.app.services.harness.metrics import tokens_per_second
from src.app.services.harness.reviewers import build_failed_feedback, run_single_reviewer
from src.app.services.llm_service.together import call_together
from src.app.services.model_context import (
    build_initial_generator_prompt,
    build_retry_generator_prompt,
    build_reviewer_input,
    read_changed_file_contents,
)
from src.app.services.workspace import cleanup_workspace, create_workspace
from src.app.utils.io import write_json, write_text


async def run_harness(req: RunHarnessRequest) -> RunHarnessResponse:
    """
    Execute a single harness run.

    The original repository is never mutated during iteration. All generator
    operations are applied to an isolated worktree. Only when every reviewer
    approves is the final diff applied back to the original repository.

    Returns a RunHarnessResponse containing approval state, final diff,
    execution trace and aggregated metrics.
    """
    start = time.time()

    execution_plan = (
        req.execution_plan
        if req.execution_plan is not None
        else build_static_execution_plan(req)
    )
    generator_instructions = build_assignment_instructions(
        role='generator',
        persona_id=execution_plan.generator.persona,
        skill_ids=execution_plan.generator.skills,
        focus=execution_plan.generator.focus,
    )

    workspace = create_workspace(req.repo_path)

    write_json(workspace.run_path, 'request.json', req.model_dump())
    write_json(
        workspace.run_path,
        'execution-plan.json',
        execution_plan.model_dump(),
    )

    trace = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cached_input_tokens = 0
    total_reasoning_tokens = 0
    final_diff = ''
    approved = False

    previous_generator_output = ''
    reviewer_feedback = ''

    try:
        for iteration in range(1, req.max_iterations + 1):
            repo_context = build_repo_context(str(workspace.worktree_path))

            if iteration == 1:
                base_prompt = build_initial_generator_prompt(
                    repo_context=repo_context,
                    user_prompt=req.prompt,
                )
            else:
                base_prompt = build_retry_generator_prompt(
                    repo_context=repo_context,
                    user_prompt=req.prompt,
                    previous_generator_output=previous_generator_output,
                    reviewer_feedback=reviewer_feedback,
                )

            current_prompt = combine_generator_prompt(
                assignment_instructions=generator_instructions,
                task_prompt=base_prompt,
            )

            write_text(
                workspace.run_path,
                f'generator/iteration-{iteration}-prompt.txt',
                current_prompt,
            )

            gen = await call_together(
                req.generator_model,
                current_prompt,
            )

            write_json(
                workspace.run_path,
                f'generator/iteration-{iteration}-response.json',
                gen,
            )

            generator_metrics = ModelMetrics(
                model=req.generator_model,
                input_tokens=gen['input_tokens'],
                output_tokens=gen['output_tokens'],
                cached_input_tokens=gen.get('cached_input_tokens', 0),
                reasoning_tokens=gen.get('reasoning_tokens', 0),
                duration_ms=gen['duration_ms'],
                tokens_per_second=tokens_per_second(
                    gen['input_tokens'],
                    gen['output_tokens'],
                    gen['duration_ms'],
                ),
            )

            try:
                if gen.get('reached_output_limit'):
                    finish_reason = gen.get('finish_reason') or 'unknown'

                    raise ValueError(
                        'Generator output reached its maximum output length. '
                        f'finish_reason={finish_reason}; '
                        f"max_output_tokens={gen.get('max_output_tokens')}"
                    )

                operations = parse_file_operations(gen['text'])

                write_json(
                    workspace.run_path,
                    f'generator/iteration-{iteration}-operations.json',
                    {'operations': operations},
                )

                apply_file_operations(
                    str(workspace.worktree_path),
                    operations,
                )

                final_diff = get_git_diff(str(workspace.worktree_path))
                changed_files = get_changed_files(str(workspace.worktree_path))
                changed_file_contents = read_changed_file_contents(
                    str(workspace.worktree_path),
                    changed_files,
                )

                write_text(
                    workspace.run_path,
                    f'diffs/iteration-{iteration}.diff',
                    final_diff,
                )

                review_input = build_reviewer_input(
                    user_prompt=req.prompt,
                    final_diff=final_diff,
                    changed_file_contents=changed_file_contents,
                )

                reviewer_calls = [
                    run_single_reviewer(
                        req=req,
                        assignment=assignment,
                        reviewer_index=reviewer_index,
                        phase=execution_plan.phase,
                        review_input=review_input,
                        iteration=iteration,
                        run_id=workspace.run_id,
                        run_path=workspace.run_path,
                    )
                    for reviewer_index, assignment in enumerate(
                        execution_plan.reviewers,
                        start=1,
                    )
                ]
                reviewer_results = await asyncio.gather(*reviewer_calls)

            # TODO: Split system errors from reviewer results.
            # File operation failures are currently represented as a synthetic
            # "system" reviewer so the loop can continue, but the response
            # model should eventually expose explicit system_errors.
            # Keep the loop alive and convert operation-level failures into a
            # synthetic review result until system_errors is modeled explicitly.
            except Exception as exc:  # pylint: disable=broad-exception-caught
                system_review_metrics = ReviewerMetrics(
                    persona='system',
                    skills=[],
                    model='system',
                    input_tokens=0,
                    output_tokens=0,
                    duration_ms=0,
                    tokens_per_second=0,
                )

                reviewer_results = [
                    ReviewerResult(
                        persona='system',
                        skills=[],
                        focus='Report harness infrastructure failures.',
                        model='system',
                        run_id=workspace.run_id,
                        iteration=iteration,
                        phase=execution_plan.phase,
                        strictness=100,
                        score=0,
                        blocking_issues=[
                            {
                                'title': 'File operation failure',
                                'description': str(exc),
                                'file': None,
                            }
                        ],
                        feedback=f'File operations failed: {exc}',
                        approved=False,
                        metrics=system_review_metrics,
                    )
                ]

            reviewers_metrics = [
                result.metrics
                for result in reviewer_results
            ]
            iteration_approved = all(
                result.approved
                for result in reviewer_results
            )
            iteration_feedback = build_failed_feedback(reviewer_results)

            total_input_tokens += generator_metrics.input_tokens
            total_output_tokens += generator_metrics.output_tokens
            total_cached_input_tokens += generator_metrics.cached_input_tokens
            total_reasoning_tokens += generator_metrics.reasoning_tokens

            for metrics in reviewers_metrics:
                total_input_tokens += metrics.input_tokens
                total_output_tokens += metrics.output_tokens
                total_cached_input_tokens += metrics.cached_input_tokens
                total_reasoning_tokens += metrics.reasoning_tokens

            trace.append(
                {
                    'iteration': iteration,
                    'generator_output': gen['text'],
                    'reviewer_feedback': iteration_feedback,
                    'approved': iteration_approved,
                    'generator_metrics': generator_metrics,
                    'reviewers': reviewer_results,
                    'reviewers_metrics': reviewers_metrics,
                }
            )

            if iteration_approved:
                approved = True
                break

            previous_generator_output = gen['text']
            reviewer_feedback = iteration_feedback

        if approved and final_diff:
            valid, error = validate_patch(
                req.repo_path,
                final_diff,
            )
            if not valid:
                raise RuntimeError(
                    'Final diff does not apply to original repo: '
                    f'{error}'
                )

            applied, error = apply_patch(
                req.repo_path,
                final_diff,
            )
            if not applied:
                raise RuntimeError(
                    'Could not apply final diff to original repo: '
                    f'{error}'
                )

            write_text(
                workspace.run_path,
                'final.diff',
                final_diff,
            )

        duration_ms = int((time.time() - start) * 1000)
        total_tokens = total_input_tokens + total_output_tokens

        response = RunHarnessResponse(
            run_id=workspace.run_id,
            final_output=final_diff,
            approved=approved,
            execution_trace=trace,
            run_metrics=RunMetrics(
                iterations=len(trace),
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cached_input_tokens=total_cached_input_tokens,
                reasoning_tokens=total_reasoning_tokens,
                duration_ms=duration_ms,
                tokens_per_second=round(
                    total_tokens / max(duration_ms / 1000, 0.001),
                    2,
                ),
                estimated_cost_eur=0.0,
            ),
        )

        write_json(
            workspace.run_path,
            'response.json',
            response.model_dump(),
        )
        write_json(
            workspace.run_path,
            'trace.json',
            [
                item.model_dump()
                for item in response.execution_trace
            ],
        )
        write_json(
            workspace.run_path,
            'metrics.json',
            response.run_metrics.model_dump(),
        )

        return response

    finally:
        cleanup_workspace(workspace)
