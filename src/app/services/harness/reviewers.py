"""Reviewer execution helpers for harness service."""

from src.app.schemas import ReviewerAssignment, ReviewerMetrics, ReviewerResult, RunHarnessRequest
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibrary,
)
from src.app.services.llm_service.openai import review_with_openai
from src.app.services.instructions import build_assignment_instructions
from src.app.utils.metrics import tokens_per_second


def build_reviewer_metrics(
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


async def run_single_reviewer(
    *,
    req: RunHarnessRequest,
    assignment: ReviewerAssignment,
    phase: str,
    review_input: str,
    iteration: int,
    run_id: str,
    instruction_library: ExecutionInstructionLibrary,
) -> ReviewerResult:
    """Execute one persona-plus-skills reviewer."""
    reviewer_instructions = build_assignment_instructions(
        role='reviewer',
        persona_content=instruction_library.persona_content(
            assignment.persona
        ),
        skill_contents=instruction_library.skill_contents(
            assignment.skills
        ),
        focus=assignment.focus,
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
        review['score'] >= assignment.strictness
        and not review['blocking_issues']
    )

    metrics = build_reviewer_metrics(
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
        score=review['score'],
        blocking_issues=review['blocking_issues'],
        feedback=review['feedback'],
        approved=approved,
        metrics=metrics,
    )


def build_failed_feedback(
    reviewer_results: list[ReviewerResult],
) -> str:
    """Consolidate failed reviewer output for the next generator iteration."""
    failed_feedback = []

    for result in reviewer_results:
        if result.approved:
            continue

        issue_text = '\n'.join(
            f'- {issue.title}: {issue.description}'
            for issue in result.blocking_issues
        )
        skills = ', '.join(result.skills) or 'no skills'

        failed_feedback.append(
            f'[persona={result.persona}; skills={skills}] '
            f'score={result.score}, required={result.strictness}\n'
            f'{issue_text}\n'
            f'{result.feedback}'
        )

    return '\n\n'.join(failed_feedback)
