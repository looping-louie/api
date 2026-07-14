"""Controller for single-task execution."""

import asyncio

from src.app.schemas import (
    PlanTaskRequest,
    PlanTaskResponse,
    ReviewTaskRequest,
    ReviewTaskResponse,
    ReviewerAssignment,
    ReviewerMetrics,
    ReviewerResult,
    RunHarnessRequest,
    RunHarnessResult,
)
from src.app.schemas.task import RunRequest as RunTaskRequest
from src.app.schemas.task import RunResponse as RunTaskResponse
from src.app.schemas.workflow import CompletedTask
from src.app.services.execution_planner import create_execution_plan
from src.app.services.git import commit_all, has_changes
from src.app.services.harness import run_harness
from src.app.services.harness.instructions import build_assignment_instructions
from src.app.services.harness.metrics import tokens_per_second
from src.app.services.harness.reviewers import build_failed_feedback
from src.app.services.llm_service.openai import review_with_openai
from src.app.services.model_context import build_reviewer_input


async def plan_task(req: PlanTaskRequest) -> PlanTaskResponse:
    """Build the execution plan for one task without running harness."""
    execution_plan = await create_execution_plan(
        model=req.planner_model,
        task_prompt=req.prompt,
        project_profile=req.project_profile.model_dump(),
        constitution=req.constitution,
        required_skills=req.required_reviewer_skills,
        generator_persona=req.generator_persona,
    )

    return PlanTaskResponse(
        ok=True,
        task_id=req.task_id,
        execution_plan=execution_plan,
    )


async def review_task(req: ReviewTaskRequest) -> ReviewTaskResponse:
    """Review one CLI-provided candidate artifact using the planned team."""
    changed_file_contents = _build_changed_file_contents(req)

    review_input = build_reviewer_input(
        user_prompt=req.prompt,
        final_diff=req.final_diff,
        changed_file_contents=changed_file_contents,
    )

    reviewer_calls = [
        _run_reviewer_decision(
            req=req,
            assignment=assignment,
            review_input=review_input,
        )
        for assignment in req.execution_plan.reviewers
    ]

    reviewers = await asyncio.gather(*reviewer_calls)
    reviewers_metrics = [
        reviewer.metrics
        for reviewer in reviewers
    ]
    reviewer_feedback = build_failed_feedback(reviewers)
    approved = all(reviewer.approved for reviewer in reviewers)

    return ReviewTaskResponse(
        ok=True,
        run_id=req.run_id,
        task_id=req.task_id,
        iteration=req.iteration,
        approved=approved,
        reviewer_feedback=reviewer_feedback,
        reviewers=reviewers,
        reviewers_metrics=reviewers_metrics,
    )


def _build_changed_file_contents(req: ReviewTaskRequest) -> str:
    """Build reviewer file-context text from structured or raw request input."""
    if req.changed_files:
        return '\n\n'.join(
            [
                f'## {changed_file.path}\n{changed_file.content}'
                for changed_file
                in req.changed_files
            ]
        )

    # Transitional fallback for preformatted client payloads.
    # Keep this while CLI migration is incomplete.
    return req.changed_file_contents or ''


async def _run_reviewer_decision(
    *,
    req: ReviewTaskRequest,
    assignment: ReviewerAssignment,
    review_input: str,
) -> ReviewerResult:
    """Execute one reviewer assignment for /task/review."""
    reviewer_instructions = build_assignment_instructions(
        role='reviewer',
        persona_id=assignment.persona,
        skill_ids=assignment.skills,
        focus=assignment.focus,
    )
    review = await review_with_openai(
        model=req.reviewer_model,
        original_prompt=req.prompt,
        candidate_output=review_input,
        reviewer_instructions=reviewer_instructions,
        phase=req.execution_plan.phase,
        strictness=assignment.strictness,
        focus=assignment.focus,
        constitution=req.constitution,
    )

    approved = (
        review['score'] >= assignment.strictness
        and not review['blocking_issues']
    )
    metrics = ReviewerMetrics(
        persona=assignment.persona,
        skills=assignment.skills,
        model=req.reviewer_model,
        input_tokens=review['input_tokens'],
        output_tokens=review['output_tokens'],
        cached_input_tokens=review.get('cached_input_tokens', 0),
        reasoning_tokens=review.get('reasoning_tokens', 0),
        duration_ms=review['duration_ms'],
        tokens_per_second=tokens_per_second(
            review['input_tokens'],
            review['output_tokens'],
            review['duration_ms'],
        ),
    )

    return ReviewerResult(
        persona=assignment.persona,
        skills=assignment.skills,
        focus=assignment.focus,
        model=req.reviewer_model,
        run_id=req.run_id,
        iteration=req.iteration,
        phase=req.execution_plan.phase,
        strictness=assignment.strictness,
        score=review['score'],
        blocking_issues=review['blocking_issues'],
        feedback=review['feedback'],
        approved=approved,
        metrics=metrics,
    )


async def run_task(req: RunTaskRequest) -> RunTaskResponse:
    """
    Execute one task using the same flow used by workflow execution.

    Transitional note:
    This path keeps API-side harness execution available while CLI-side
    execution contracts mature. If migration is aborted, this remains valid.
    """
    task = req.task.model_dump()

    if task['status'] != 'pending':
        return RunTaskResponse(
            ok=False,
            status='stopped',
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

    run_harness_result: RunHarnessResult = await run_harness(
        RunHarnessRequest(
            repo_path=req.repo_path,
            prompt=task['prompt'],
            max_iterations=req.max_iterations,
            generator_model=req.generator_model,
            reviewer_model=req.reviewer_model,
            execution_plan=execution_plan,
            constitution=constitution,
        )
    )

    # RunHarness Outcome Evaluation

    if not run_harness_result.approved:
        return RunTaskResponse(
            ok=False,
            status='stopped',
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=False,
            message=(
                'Stopped because reviewers did not approve within '
                'max_iterations.'
            ),
        )

    elif not has_changes(req.repo_path):
        return RunTaskResponse(
            ok=False,
            status='stopped',
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=True,
            message=(
                'Run approved but no repository changes were found '
                'to commit.'
            ),
        )

    else:
        commit_sha = commit_all(
            repo_path=req.repo_path,
            message=task['commit_message'],
        )

        return RunTaskResponse(
            ok=True,
            status='completed',
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=True,
            message='Task completed and committed.',
            completed=CompletedTask(
                task_id=task['id'],
                run_id=run_harness_result.run_id,
                commit_sha=commit_sha,
                commit_message=task['commit_message'],
                phase=execution_plan.phase,
                reasoning=execution_plan.reasoning,
                generator=execution_plan.generator,
                reviewers=execution_plan.reviewers,
            ),
    )
