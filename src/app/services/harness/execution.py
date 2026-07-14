"""Execution helpers for one harness iteration."""

import asyncio

from src.app.models.workspace import Workspace
from src.app.schemas import (
    ExecutionPlan,
    ReviewerMetrics,
    ReviewerResult,
    RunHarnessRequest,
)
from src.app.services.harness.ports import HarnessExecutionPorts
from src.app.services.harness.reviewers import run_single_reviewer
from src.app.services.model_context import build_reviewer_input, read_changed_file_contents
from src.app.utils.io import write_json, write_text


async def execute_iteration_and_review(
    *,
    req: RunHarnessRequest,
    execution_plan: ExecutionPlan,
    ports: HarnessExecutionPorts,
    workspace: Workspace,
    iteration: int,
    generator_output: str,
) -> tuple[str, list[ReviewerResult]]:
    """Apply generator operations and execute all reviewers."""
    operations = ports.filesystem.parse_file_operations(generator_output)

    write_json(
        workspace.run_path,
        f'generator/iteration-{iteration}-operations.json',
        {'operations': operations},
    )

    ports.filesystem.apply_file_operations(
        str(workspace.worktree_path),
        operations,
    )

    final_diff = ports.git.get_git_diff(str(workspace.worktree_path))
    changed_files = ports.git.get_changed_files(str(workspace.worktree_path))
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
    return final_diff, reviewer_results


def build_system_failure_result(
    *,
    run_id: str,
    iteration: int,
    phase: str,
    error: Exception,
) -> list[ReviewerResult]:
    """Convert harness infrastructure failures to a synthetic reviewer."""
    system_review_metrics = ReviewerMetrics(
        persona='system',
        skills=[],
        model='system',
        input_tokens=0,
        output_tokens=0,
        duration_ms=0,
        tokens_per_second=0,
    )

    return [
        ReviewerResult(
            persona='system',
            skills=[],
            focus='Report harness infrastructure failures.',
            model='system',
            run_id=run_id,
            iteration=iteration,
            phase=phase,
            strictness=100,
            score=0,
            blocking_issues=[
                {
                    'title': 'File operation failure',
                    'description': str(error),
                    'file': None,
                }
            ],
            feedback=f'File operations failed: {error}',
            approved=False,
            metrics=system_review_metrics,
        )
    ]
