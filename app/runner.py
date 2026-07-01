import time

from app.file_ops import apply_file_operations, parse_file_operations
from app.llm_openai import review_with_openai
from app.llm_together import call_together
from app.patcher import apply_patch, get_changed_files, get_git_diff, validate_patch
from app.prompt_builder import (
    build_initial_generator_prompt,
    build_retry_generator_prompt,
    build_reviewer_input,
)
from app.repository import build_snapshot, format_snapshot_for_prompt, read_changed_file_contents
from app.schemas import ModelMetrics, ReviewerMetrics, RunMetrics, RunRequest, RunResponse
from app.workspace import create_workspace


def _tokens_per_second(input_tokens: int, output_tokens: int, duration_ms: int) -> float:
    total_tokens = input_tokens + output_tokens
    return round(total_tokens / max(duration_ms / 1000, 0.001), 2)


def _build_repo_context(worktree_path: str) -> str:
    snapshot = build_snapshot(worktree_path)
    return format_snapshot_for_prompt(snapshot)


async def run_harness(req: RunRequest) -> RunResponse:
    start = time.time()
    workspace = create_workspace(req.repo_path)

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

            gen = await call_together(req.generator_model, current_prompt)

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
                apply_file_operations(str(workspace.worktree_path), operations)

                final_diff = get_git_diff(str(workspace.worktree_path))
                changed_files = get_changed_files(str(workspace.worktree_path))
                changed_file_contents = read_changed_file_contents(
                    str(workspace.worktree_path),
                    changed_files,
                )

                review_input = build_reviewer_input(
                    user_prompt=req.prompt,
                    final_diff=final_diff,
                    changed_file_contents=changed_file_contents,
                )

                review = await review_with_openai(
                    model=req.reviewer_model,
                    original_prompt=req.prompt,
                    candidate_output=review_input,
                    skill=req.skill,
                )

            except Exception as exc:
                review = {
                    "approved": False,
                    "feedback": f"File operations failed: {exc}",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cached_input_tokens": 0,
                    "reasoning_tokens": 0,
                    "duration_ms": 0,
                }

            reviewer_metrics = ReviewerMetrics(
                skill=req.skill,
                model=req.reviewer_model,
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

            total_input_tokens += generator_metrics.input_tokens + reviewer_metrics.input_tokens
            total_output_tokens += generator_metrics.output_tokens + reviewer_metrics.output_tokens
            total_cached_input_tokens += generator_metrics.cached_input_tokens + reviewer_metrics.cached_input_tokens
            total_reasoning_tokens += generator_metrics.reasoning_tokens + reviewer_metrics.reasoning_tokens

            trace.append(
                {
                    "iteration": iteration,
                    "generator_output": gen["text"],
                    "reviewer_feedback": review["feedback"],
                    "approved": review["approved"],
                    "generator_metrics": generator_metrics,
                    "reviewers_metrics": [reviewer_metrics],
                }
            )

            if review["approved"]:
                approved = True
                break

            previous_generator_output = gen["text"]
            reviewer_feedback = review["feedback"]

        if approved and final_diff:
            valid, error = validate_patch(req.repo_path, final_diff)
            if not valid:
                raise RuntimeError(f"Final diff does not apply to original repo: {error}")

            applied, error = apply_patch(req.repo_path, final_diff)
            if not applied:
                raise RuntimeError(f"Could not apply final diff to original repo: {error}")

        duration_ms = int((time.time() - start) * 1000)
        total_tokens = total_input_tokens + total_output_tokens

        return RunResponse(
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

    finally:
        workspace.cleanup()