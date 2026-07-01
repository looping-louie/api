import time

from app.file_ops import apply_file_operations, parse_file_operations
from app.llm_openai import review_with_openai
from app.llm_together import call_together
from app.patcher import apply_patch, get_changed_files, get_git_diff, validate_patch
from app.repository import build_snapshot, format_snapshot_for_prompt, read_changed_file_contents
from app.schemas import Metrics, RunRequest, RunResponse
from app.workspace import create_workspace


async def run_harness(req: RunRequest) -> RunResponse:
    start = time.time()
    workspace = create_workspace(req.repo_path)

    trace = []
    total_input_tokens = 0
    total_output_tokens = 0
    final_diff = ""
    approved = False

    try:
        snapshot = build_snapshot(str(workspace.worktree_path))
        repo_context = format_snapshot_for_prompt(snapshot)

        current_prompt = f"""
User task:

{req.prompt}

Repository context:

{repo_context}

Return ONLY JSON file operations.
Do not return a git patch.
""".strip()

        for iteration in range(1, req.max_iterations + 1):
            gen = await call_together(req.generator_model, current_prompt)

            try:
                operations = parse_file_operations(gen["text"])
                apply_file_operations(str(workspace.worktree_path), operations)

                final_diff = get_git_diff(str(workspace.worktree_path))
                changed_files = get_changed_files(str(workspace.worktree_path))
                changed_file_contents = read_changed_file_contents(
                    str(workspace.worktree_path),
                    changed_files,
                )

                review_input = f"""
Original user prompt:

{req.prompt}

Git diff:

{final_diff}

Changed files:

{changed_file_contents}
""".strip()

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
                    "duration_ms": 0,
                }

            total_input_tokens += gen["input_tokens"] + review["input_tokens"]
            total_output_tokens += gen["output_tokens"] + review["output_tokens"]

            trace.append(
                {
                    "iteration": iteration,
                    "generator_output": gen["text"],
                    "reviewer_feedback": review["feedback"],
                    "approved": review["approved"],
                    "input_tokens": gen["input_tokens"] + review["input_tokens"],
                    "output_tokens": gen["output_tokens"] + review["output_tokens"],
                    "duration_ms": gen["duration_ms"] + review["duration_ms"],
                }
            )

            if review["approved"]:
                approved = True
                break

            current_prompt = f"""
Original user prompt:

{req.prompt}

Previous generator output:

{gen["text"]}

Reviewer or system feedback:

{review["feedback"]}

Repository context:

{repo_context}

Return corrected JSON file operations only.
""".strip()

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
            final_output=final_diff if approved else "",
            execution_trace=trace,
            metrics=Metrics(
                iterations=len(trace),
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                duration_ms=duration_ms,
                tokens_per_second=round(total_tokens / max(duration_ms / 1000, 0.001), 2),
                estimated_cost_eur=0.0,
            ),
        )

    finally:
        workspace.cleanup()