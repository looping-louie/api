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
from src.app.schemas.task import (
    RunRequest as RunTaskRequest,
    RunResponse as RunTaskResponse
)
from src.app.schemas.workflow import CompletedTask
from src.app.services.execution_planner import create_execution_plan
from src.app.services.harness.adapters import build_local_harness_execution_ports
from src.app.services.instructions import build_assignment_instructions
from src.app.services.harness.runner import build_execution_run_path, run_harness
from src.app.services.harness.reviewers import build_failed_feedback
from src.app.services.llm_service.openai import review_with_openai
from src.app.services.model_context import build_reviewer_input
from src.app.services.workspace import cleanup_workspace, create_workspace
from src.app.utils.io import write_json
from src.app.utils.metrics import tokens_per_second


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
    review_input = build_reviewer_input(
        user_prompt=req.prompt,
        final_diff=req.final_diff,
        changed_file_contents=req.changed_file_contents,
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
    """Execute one task using the same flow used by workflow execution."""
    task = req.task.model_dump()

    if task['status'] != 'pending':
        return RunTaskResponse(
            ok=False,
            status='stopped',
            commit_allowed=False,
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

    generator_instructions = build_assignment_instructions(
        role='generator',
        persona_id=execution_plan.generator.persona,
        skill_ids=execution_plan.generator.skills,
        focus=execution_plan.generator.focus,
    )

    execution_ports = build_local_harness_execution_ports()
    workspace = create_workspace(req.repo_path)
    run_path = build_execution_run_path(workspace.run_id)

    write_json(
        run_path,
        'request.json',
        {
            'repo_path': req.repo_path,
            'prompt': task['prompt'],
            'constitution': constitution,
            'max_iterations': req.max_iterations,
            'generator_model': req.generator_model,
            'reviewer_model': req.reviewer_model,
        },
    )
    write_json(
        run_path,
        'execution-plan.json',
        execution_plan.model_dump(),
    )

    try:
        run_harness_result: RunHarnessResult = await run_harness(
            RunHarnessRequest(
                repo_path=req.repo_path,
                prompt=task['prompt'],
                max_iterations=req.max_iterations,
                generator_model=req.generator_model,
                reviewer_model=req.reviewer_model,
                execution_plan=execution_plan,
                constitution=constitution,
            ),
            workspace=workspace,
            run_path=run_path,
            generator_instructions=generator_instructions,
            execution_ports=execution_ports,
        )

        write_json(
            run_path,
            'response.json',
            run_harness_result.model_dump(),
        )
        write_json(
            run_path,
            'trace.json',
            [
                item.model_dump()
                for item in run_harness_result.execution_trace
            ],
        )
        write_json(
            run_path,
            'metrics.json',
            run_harness_result.run_metrics.model_dump(),
        )

        if run_harness_result.approved and run_harness_result.final_output:
            _validate_and_apply_final_diff(
                repo_path=req.repo_path,
                final_diff=run_harness_result.final_output,
                execution_ports=execution_ports,
            )
    finally:
        cleanup_workspace(workspace)

    # RunHarness Outcome Evaluation

    if not run_harness_result.approved:
        return RunTaskResponse(
            ok=False,
            status='stopped',
            commit_allowed=False,
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=False,
            message=(
                'Stopped because reviewers did not approve within '
                'max_iterations.'
            ),
        )

    else:
        return RunTaskResponse(
            ok=True,
            status='completed',
            commit_allowed=True,
            task_id=task['id'],
            run_id=run_harness_result.run_id,
            approved=True,
            message='Task approved. Commit must be executed by CLI.',
            completed=CompletedTask(
                task_id=task['id'],
                run_id=run_harness_result.run_id,
                commit_sha='deprecated API response field',
                commit_message='deprecated API response field',
                phase=execution_plan.phase,
                reasoning=execution_plan.reasoning,
                generator=execution_plan.generator,
                reviewers=execution_plan.reviewers,
            ),
        )


def _validate_and_apply_final_diff(
    *,
    repo_path: str,
    final_diff: str,
    execution_ports,
) -> None:
    """Apply an approved final diff to the original repository."""
    valid, error = execution_ports.git.validate_patch(
        repo_path,
        final_diff,
    )
    if not valid:
        raise RuntimeError(
            'Final diff does not apply to original repo: '
            f'{error}'
        )

    applied, error = execution_ports.git.apply_patch(
        repo_path,
        final_diff,
    )
    if not applied:
        raise RuntimeError(
            'Could not apply final diff to original repo: '
            f'{error}'
        )
