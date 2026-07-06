"""
Core harness runner.

This module orchestrates one Looping Louie run:

1. Create an isolated git worktree.
2. Build repository context.
3. Ask the generator model for JSON file operations.
4. Apply operations inside the worktree.
5. Generate a real git diff.
6. Run all reviewer skills in parallel.
7. Retry until reviewers approve or max_iterations is reached.
8. If approved, apply the final diff to the original repository.
9. Persist request, prompts, responses, diffs, metrics and trace.

The runner should not know provider-specific details.
Model calls live in llm_together.py and llm_openai.py.
"""

import asyncio
import time
from src.app.services.file_change_service import apply_file_operations, parse_file_operations
from src.app.llm_openai import review_with_openai
from src.app.llm_together import call_together
from src.app.services.git_service import apply_patch, get_changed_files, get_git_diff, validate_patch
from src.app.services.model_context_service import (
    build_initial_generator_prompt,
    build_retry_generator_prompt,
    build_reviewer_input,
    build_snapshot,
    format_snapshot_for_prompt,
    read_changed_file_contents,
)
from src.app.utils.io import write_json, write_text
from src.app.schemas import (
    ModelMetrics,
    ReviewerMetrics,
    ReviewerResult,
    RunMetrics,
    RunHarnessRequest,
    RunHarnessResponse,
)
from src.app.services.workspace_service import create_workspace


def _tokens_per_second(input_tokens: int, output_tokens: int, duration_ms: int) -> float:
    """Compute throughput for a model call."""
    total_tokens = input_tokens + output_tokens
    return round(total_tokens / max(duration_ms / 1000, 0.001), 2)


def _build_repo_context(worktree_path: str) -> str:
    """Build the prompt-ready repository snapshot for the current worktree state."""
    snapshot = build_snapshot(worktree_path)
    return format_snapshot_for_prompt(snapshot)


def _build_reviewer_metrics(skill: str, model: str, review: dict) -> ReviewerMetrics:
    """Convert a raw reviewer response into structured metrics."""
    return ReviewerMetrics(
        skill=skill,
        model=model,
        input_tokens=review["input_tokens"],
        output_tokens=review["output_tokens"],
        cached_input_tokens=review.get("cached_input_tokens", 0),
        reasoning_tokens=review.get("reasoning_tokens", 0),
        duration_ms=review["duration_ms"],
        tokens_per_second=_tokens_per_second(
            review["input_tokens"],
            review["output_tokens"],
            review["duration_ms"],
        ),
    )


async def _run_single_reviewer(
    req: RunHarnessRequest,
    skill: str,
    review_input: str,
    iteration: int,
    run_path,
) -> ReviewerResult:
    """
    Run one reviewer skill against the candidate diff.

    The prompt and response are persisted under the run folder so executions
    can be inspected after the API call finishes.
    """
    write_text(
        run_path,
        f"reviewers/{skill}/iteration-{iteration}-prompt.txt",
        review_input,
    )

    review = await review_with_openai(
        model=req.reviewer_model,
        original_prompt=req.prompt,
        candidate_output=review_input,
        skill=skill,
    )

    write_json(
        run_path,
        f"reviewers/{skill}/iteration-{iteration}-response.json",
        review,
    )

    metrics = _build_reviewer_metrics(
        skill=skill,
        model=req.reviewer_model,
        review=review,
    )

    return ReviewerResult(
        skill=skill,
        approved=review["approved"],
        feedback=review["feedback"],
        metrics=metrics,
    )


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
    workspace = create_workspace(req.repo_path)

    write_json(workspace.run_path, "request.json", req.model_dump())

    trace = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cached_input_tokens = 0
    total_reasoning_tokens = 0
    final_diff = ""
    approved = False

    previous_generator_output = ""
    reviewer_feedback = ""

    try:
        for iteration in range(1, req.max_iterations + 1):
            repo_context = _build_repo_context(str(workspace.worktree_path))

            if iteration == 1:
                current_prompt = build_initial_generator_prompt(
                    repo_context=repo_context,
                    user_prompt=req.prompt,
                )
            else:
                current_prompt = build_retry_generator_prompt(
                    repo_context=repo_context,
                    user_prompt=req.prompt,
                    previous_generator_output=previous_generator_output,
                    reviewer_feedback=reviewer_feedback,
                )

            write_text(
                workspace.run_path,
                f"generator/iteration-{iteration}-prompt.txt",
                current_prompt,
            )

            gen = await call_together(req.generator_model, current_prompt)

            write_json(
                workspace.run_path,
                f"generator/iteration-{iteration}-response.json",
                gen,
            )

            generator_metrics = ModelMetrics(
                model=req.generator_model,
                input_tokens=gen["input_tokens"],
                output_tokens=gen["output_tokens"],
                cached_input_tokens=gen.get("cached_input_tokens", 0),
                reasoning_tokens=gen.get("reasoning_tokens", 0),
                duration_ms=gen["duration_ms"],
                tokens_per_second=_tokens_per_second(
                    gen["input_tokens"],
                    gen["output_tokens"],
                    gen["duration_ms"],
                ),
            )

            try:
                operations = parse_file_operations(gen["text"])

                write_json(
                    workspace.run_path,
                    f"generator/iteration-{iteration}-operations.json",
                    {"operations": operations},
                )

                apply_file_operations(str(workspace.worktree_path), operations)

                final_diff = get_git_diff(str(workspace.worktree_path))
                changed_files = get_changed_files(str(workspace.worktree_path))
                changed_file_contents = read_changed_file_contents(
                    str(workspace.worktree_path),
                    changed_files,
                )

                write_text(
                    workspace.run_path,
                    f"diffs/iteration-{iteration}.diff",
                    final_diff,
                )

                review_input = build_reviewer_input(
                    user_prompt=req.prompt,
                    final_diff=final_diff,
                    changed_file_contents=changed_file_contents,
                )

                reviewer_results = await asyncio.gather(
                    *[
                        _run_single_reviewer(
                            req=req,
                            skill=skill,
                            review_input=review_input,
                            iteration=iteration,
                            run_path=workspace.run_path,
                        )
                        for skill in req.skills
                    ]
                )

            # TODO: Split system errors from reviewer results.
            # File operation failures are currently represented as a synthetic "system"
            # reviewer so the loop can continue, but the response model should eventually
            # expose explicit system_errors.
            except Exception as exc:
                system_review_metrics = ReviewerMetrics(
                    skill="system",
                    model="system",
                    input_tokens=0,
                    output_tokens=0,
                    duration_ms=0,
                    tokens_per_second=0,
                )

                reviewer_results = [
                    ReviewerResult(
                        skill="system",
                        approved=False,
                        feedback=f"File operations failed: {exc}",
                        metrics=system_review_metrics,
                    )
                ]

            reviewers_metrics = [result.metrics for result in reviewer_results]
            iteration_approved = all(result.approved for result in reviewer_results)

            failed_feedback = [
                f"[{result.skill}] {result.feedback}"
                for result in reviewer_results
                if not result.approved
            ]

            reviewer_feedback = (
                "\n\n".join(failed_feedback)
                if failed_feedback
                else "\n\n".join(
                    f"[{result.skill}] {result.feedback}"
                    for result in reviewer_results
                )
            )

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
                    "iteration": iteration,
                    "generator_output": gen["text"],
                    "reviewer_feedback": reviewer_feedback,
                    "approved": iteration_approved,
                    "generator_metrics": generator_metrics,
                    "reviewers": reviewer_results,
                    "reviewers_metrics": reviewers_metrics,
                }
            )

            if iteration_approved:
                approved = True
                break

            previous_generator_output = gen["text"]

        if approved and final_diff:
            valid, error = validate_patch(req.repo_path, final_diff)
            if not valid:
                raise RuntimeError(f"Final diff does not apply to original repo: {error}")

            applied, error = apply_patch(req.repo_path, final_diff)
            if not applied:
                raise RuntimeError(f"Could not apply final diff to original repo: {error}")

            write_text(workspace.run_path, "final.diff", final_diff)

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
                tokens_per_second=round(total_tokens / max(duration_ms / 1000, 0.001), 2),
                estimated_cost_eur=0.0,
            ),
        )

        write_json(workspace.run_path, "response.json", response.model_dump())
        write_json(
            workspace.run_path,
            "trace.json",
            [item.model_dump() for item in response.execution_trace],
        )
        write_json(workspace.run_path, "metrics.json", response.run_metrics.model_dump())

        return response

    finally:
        workspace.cleanup()
