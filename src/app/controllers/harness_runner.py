"""
Core harness runner.

This module orchestrates one Looping Louie run:

1. Create an isolated git worktree.
2. Build repository context.
3. Ask the generator model for JSON file operations.
4. Apply operations inside the worktree.
5. Generate a real git diff.
6. Run all assigned reviewers in parallel.
7. Retry until reviewers approve or max_iterations is reached.
8. If approved, apply the final diff to the original repository.
9. Persist request, prompts, responses, diffs, metrics and trace.

The runner should not know provider-specific details.
Model calls live in the provider-specific LLM service modules.
"""

import asyncio
import re
import time
from pathlib import Path

from src.app.personas import load_persona
from src.app.schemas import (
    ExecutionPlan,
    GeneratorAssignment,
    ModelMetrics,
    ReviewerAssignment,
    ReviewerMetrics,
    ReviewerResult,
    RunHarnessRequest,
    RunHarnessResponse,
    RunMetrics,
)
from src.app.services.file_change_service import (
    apply_file_operations,
    parse_file_operations,
)
from src.app.services.git_service import (
    apply_patch,
    get_changed_files,
    get_git_diff,
    validate_patch,
)
from src.app.services.llm_service.openai import review_with_openai
from src.app.services.llm_service.together import call_together
from src.app.services.model_context_service import (
    build_initial_generator_prompt,
    build_retry_generator_prompt,
    build_reviewer_input,
    build_snapshot,
    format_snapshot_for_prompt,
    read_changed_file_contents,
)
from src.app.services.workspace_service import (
    cleanup_workspace,
    create_workspace,
)
from src.app.skills import load_skill
from src.app.utils.io import write_json, write_text


def _tokens_per_second(
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
) -> float:
    """Compute throughput for a model call."""
    total_tokens = input_tokens + output_tokens
    return round(
        total_tokens / max(duration_ms / 1000, 0.001),
        2,
    )


def _build_repo_context(worktree_path: str) -> str:
    """Build the prompt-ready repository snapshot for the current worktree state."""
    snapshot = build_snapshot(worktree_path)
    return format_snapshot_for_prompt(snapshot)


def _build_assignment_instructions(
    *,
    role: str,
    persona_id: str,
    skill_ids: list[str],
    focus: str,
) -> str:
    """
    Build provider-agnostic instructions from one persona and its skills.

    Loaders own filesystem lookup and registry validation. The harness only
    combines their content for the model call.
    """
    persona_content = load_persona(persona_id).strip()
    skill_contents = [
        load_skill(skill_id).strip()
        for skill_id in skill_ids
    ]

    sections = [
        f"# {role.title()} assignment",
        "## Persona",
        persona_content,
    ]

    if skill_contents:
        sections.extend(
            [
                "## Assigned skills",
                "\n\n---\n\n".join(skill_contents),
            ]
        )

    sections.extend(
        [
            "## Task-specific focus",
            focus.strip(),
        ]
    )

    return "\n\n".join(sections)


def _combine_generator_prompt(
    *,
    assignment_instructions: str,
    task_prompt: str,
) -> str:
    """Place assignment context before the existing generator contract."""
    return (
        f"{assignment_instructions}\n\n"
        "# Execution instructions\n\n"
        f"{task_prompt}"
    )


def _build_static_execution_plan(req: RunHarnessRequest) -> ExecutionPlan:
    """
    Build a deterministic fallback for direct harness calls.

    Planned task runs should supply execution_plan. This fallback preserves the
    low-level API for callers that want to configure the harness explicitly.
    """
    if not req.reviewer_skills:
        raise ValueError(
            "At least one reviewer skill is required without an execution plan"
        )

    return ExecutionPlan(
        phase="mvp",
        reasoning="Static execution configuration supplied by the caller.",
        generator=GeneratorAssignment(
            persona=req.generator_persona,
            skills=req.generator_skills,
            focus="Implement the requested change with minimal safe modifications.",
        ),
        reviewers=[
            ReviewerAssignment(
                persona=req.reviewer_persona,
                skills=[skill_id],
                strictness=55,
                focus="Review the requested change using the assigned skill.",
            )
            for skill_id in req.reviewer_skills
        ],
    )


def _reviewer_key(
    *,
    reviewer_index: int,
    assignment: ReviewerAssignment,
) -> str:
    """Build a unique filesystem-safe identifier for one reviewer."""
    persona_slug = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "-",
        assignment.persona,
    ).strip("-")

    return f"reviewer-{reviewer_index:02d}-{persona_slug or 'unknown'}"


def _build_reviewer_metrics(
    *,
    assignment: ReviewerAssignment,
    model: str,
    review: dict,
) -> ReviewerMetrics:
    """Convert a raw reviewer response into structured metrics."""
    return ReviewerMetrics(
        persona=assignment.persona,
        skills=assignment.skills,
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
    *,
    req: RunHarnessRequest,
    assignment: ReviewerAssignment,
    reviewer_index: int,
    phase: str,
    review_input: str,
    iteration: int,
    run_id: str,
    run_path: Path,
) -> ReviewerResult:
    """Execute and persist one persona-plus-skills reviewer."""
    reviewer_key = _reviewer_key(
        reviewer_index=reviewer_index,
        assignment=assignment,
    )
    reviewer_instructions = _build_assignment_instructions(
        role="reviewer",
        persona_id=assignment.persona,
        skill_ids=assignment.skills,
        focus=assignment.focus,
    )

    write_text(
        run_path,
        f"reviewers/{reviewer_key}/iteration-{iteration}-prompt.txt",
        (
            f"{reviewer_instructions}\n\n"
            "# Candidate change\n\n"
            f"{review_input}"
        ),
    )

    review = await review_with_openai(
        model=req.reviewer_model,
        original_prompt=req.prompt,
        candidate_output=review_input,
        reviewer_instructions=reviewer_instructions,
        phase=phase,
        strictness=assignment.strictness,
        focus=assignment.focus,
        constitution=req.constitution,
    )

    approved = (
        review["score"] >= assignment.strictness
        and not review["blocking_issues"]
    )

    persisted_review = {
        "run_id": run_id,
        "iteration": iteration,
        "persona": assignment.persona,
        "skills": assignment.skills,
        "focus": assignment.focus,
        "model": req.reviewer_model,
        "phase": phase,
        "strictness": assignment.strictness,
        "approved": approved,
        **review,
    }

    write_json(
        run_path,
        f"reviewers/{reviewer_key}/iteration-{iteration}-response.json",
        persisted_review,
    )

    metrics = _build_reviewer_metrics(
        assignment=assignment,
        model=req.reviewer_model,
        review=review,
    )

    return ReviewerResult(
        persona=assignment.persona,
        skills=assignment.skills,
        focus=assignment.focus,
        model=req.reviewer_model,
        run_id=run_id,
        iteration=iteration,
        phase=phase,
        strictness=assignment.strictness,
        score=review["score"],
        blocking_issues=review["blocking_issues"],
        feedback=review["feedback"],
        approved=approved,
        metrics=metrics,
    )


def _build_failed_feedback(
    reviewer_results: list[ReviewerResult],
) -> str:
    """Consolidate failed reviewer output for the next generator iteration."""
    failed_feedback = []

    for result in reviewer_results:
        if result.approved:
            continue

        issue_text = "\n".join(
            f"- {issue.title}: {issue.description}"
            for issue in result.blocking_issues
        )
        skills = ", ".join(result.skills) or "no skills"

        failed_feedback.append(
            f"[persona={result.persona}; skills={skills}] "
            f"score={result.score}, required={result.strictness}\n"
            f"{issue_text}\n"
            f"{result.feedback}"
        )

    return "\n\n".join(failed_feedback)


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
        else _build_static_execution_plan(req)
    )
    generator_instructions = _build_assignment_instructions(
        role="generator",
        persona_id=execution_plan.generator.persona,
        skill_ids=execution_plan.generator.skills,
        focus=execution_plan.generator.focus,
    )

    workspace = create_workspace(req.repo_path)

    write_json(workspace.run_path, "request.json", req.model_dump())
    write_json(
        workspace.run_path,
        "execution-plan.json",
        execution_plan.model_dump(),
    )

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
            repo_context = _build_repo_context(
                str(workspace.worktree_path)
            )

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

            current_prompt = _combine_generator_prompt(
                assignment_instructions=generator_instructions,
                task_prompt=base_prompt,
            )

            write_text(
                workspace.run_path,
                f"generator/iteration-{iteration}-prompt.txt",
                current_prompt,
            )

            gen = await call_together(
                req.generator_model,
                current_prompt,
            )

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

                if gen.get("reached_output_limit"):
                    finish_reason = gen.get("finish_reason") or "unknown"

                    raise ValueError(
                        "Generator output reached its maximum output length. "
                        f"finish_reason={finish_reason}; "
                        f"max_output_tokens={gen.get('max_output_tokens')}"
                    )

                operations = parse_file_operations(gen["text"])

                write_json(
                    workspace.run_path,
                    f"generator/iteration-{iteration}-operations.json",
                    {"operations": operations},
                )

                apply_file_operations(
                    str(workspace.worktree_path),
                    operations,
                )

                final_diff = get_git_diff(
                    str(workspace.worktree_path)
                )
                changed_files = get_changed_files(
                    str(workspace.worktree_path)
                )
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
                )

            # TODO: Split system errors from reviewer results.
            # File operation failures are currently represented as a synthetic
            # "system" reviewer so the loop can continue, but the response
            # model should eventually expose explicit system_errors.
            except Exception as exc:
                system_review_metrics = ReviewerMetrics(
                    persona="system",
                    skills=[],
                    model="system",
                    input_tokens=0,
                    output_tokens=0,
                    duration_ms=0,
                    tokens_per_second=0,
                )

                reviewer_results = [
                    ReviewerResult(
                        persona="system",
                        skills=[],
                        focus="Report harness infrastructure failures.",
                        model="system",
                        run_id=workspace.run_id,
                        iteration=iteration,
                        phase=execution_plan.phase,
                        strictness=100,
                        score=0,
                        blocking_issues=[
                            {
                                "title": "File operation failure",
                                "description": str(exc),
                                "file": None,
                            }
                        ],
                        feedback=f"File operations failed: {exc}",
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
            iteration_feedback = _build_failed_feedback(
                reviewer_results
            )

            total_input_tokens += generator_metrics.input_tokens
            total_output_tokens += generator_metrics.output_tokens
            total_cached_input_tokens += (
                generator_metrics.cached_input_tokens
            )
            total_reasoning_tokens += (
                generator_metrics.reasoning_tokens
            )

            for metrics in reviewers_metrics:
                total_input_tokens += metrics.input_tokens
                total_output_tokens += metrics.output_tokens
                total_cached_input_tokens += metrics.cached_input_tokens
                total_reasoning_tokens += metrics.reasoning_tokens

            trace.append(
                {
                    "iteration": iteration,
                    "generator_output": gen["text"],
                    "reviewer_feedback": iteration_feedback,
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
            reviewer_feedback = iteration_feedback

        if approved and final_diff:
            valid, error = validate_patch(
                req.repo_path,
                final_diff,
            )
            if not valid:
                raise RuntimeError(
                    "Final diff does not apply to original repo: "
                    f"{error}"
                )

            applied, error = apply_patch(
                req.repo_path,
                final_diff,
            )
            if not applied:
                raise RuntimeError(
                    "Could not apply final diff to original repo: "
                    f"{error}"
                )

            write_text(
                workspace.run_path,
                "final.diff",
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
            "response.json",
            response.model_dump(),
        )
        write_json(
            workspace.run_path,
            "trace.json",
            [
                item.model_dump()
                for item in response.execution_trace
            ],
        )
        write_json(
            workspace.run_path,
            "metrics.json",
            response.run_metrics.model_dump(),
        )

        return response

    finally:
        cleanup_workspace(workspace)
