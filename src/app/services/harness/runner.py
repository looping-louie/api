"""Main harness orchestration workflow."""

import time

from src.app.schemas import (
    ModelMetrics,
    RunHarnessRequest,
    RunHarnessResult,
    RunMetrics,
)
from src.app.services.harness.adapters import build_local_harness_execution_ports
from src.app.services.harness.decision import (
    build_generator_base_prompt,
    is_iteration_approved,
)
from src.app.services.harness.execution import (
    build_system_failure_result,
    execute_iteration_and_review,
)
from src.app.services.harness.ports import HarnessExecutionPorts
from src.app.services.harness.execution_plan import build_static_execution_plan
from src.app.services.harness.instructions import (
    build_assignment_instructions,
    combine_generator_prompt,
)
from src.app.services.harness.metrics import tokens_per_second
from src.app.services.harness.reviewers import build_failed_feedback
from src.app.services.llm_service.together import call_together
from src.app.services.model_context import (
    build_snapshot,
    format_snapshot_for_prompt,
)
from src.app.utils.io import write_json, write_text


async def run_harness(
    req: RunHarnessRequest,
    execution_ports: HarnessExecutionPorts | None = None,
) -> RunHarnessResult:
    """
    Execute a single harness run.

    The original repository is never mutated during iteration. All generator
    operations are applied to an isolated worktree. Only when every reviewer
    approves is the final diff applied back to the original repository.

    Returns a RunHarnessResult containing approval state, final diff,
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

    ports = execution_ports or build_local_harness_execution_ports()

    workspace = ports.workspace.create_workspace(req.repo_path)

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
            repo_context = format_snapshot_for_prompt(
                build_snapshot(str(workspace.worktree_path))
            )

            base_prompt = build_generator_base_prompt(
                iteration=iteration,
                repo_context=repo_context,
                req=req,
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
                final_diff, reviewer_results = await execute_iteration_and_review(
                    req=req,
                    execution_plan=execution_plan,
                    ports=ports,
                    workspace=workspace,
                    iteration=iteration,
                    generator_output=gen['text'],
                )

            # TODO: Split system errors from reviewer results.
            # File operation failures are currently represented as a synthetic
            # "system" reviewer so the loop can continue, but the response
            # model should eventually expose explicit system_errors.
            # Keep the loop alive and convert operation-level failures into a
            # synthetic review result until system_errors is modeled explicitly.
            except Exception as exc:  # pylint: disable=broad-exception-caught
                reviewer_results = build_system_failure_result(
                    run_id=workspace.run_id,
                    iteration=iteration,
                    phase=execution_plan.phase,
                    error=exc,
                )

            reviewers_metrics = [
                result.metrics
                for result in reviewer_results
            ]
            iteration_approved = is_iteration_approved(reviewer_results)
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
            valid, error = ports.git.validate_patch(
                req.repo_path,
                final_diff,
            )
            if not valid:
                raise RuntimeError(
                    'Final diff does not apply to original repo: '
                    f'{error}'
                )

            applied, error = ports.git.apply_patch(
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

        response = RunHarnessResult(
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
        ports.workspace.cleanup_workspace(workspace)
