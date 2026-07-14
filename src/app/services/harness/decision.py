"""Decision helpers for harness orchestration."""

from src.app.schemas import ReviewerResult, RunHarnessRequest
from src.app.services.model_context import (
    build_initial_generator_prompt,
    build_retry_generator_prompt,
)


def build_generator_base_prompt(
    *,
    iteration: int,
    repo_context: str,
    req: RunHarnessRequest,
    previous_generator_output: str,
    reviewer_feedback: str,
) -> str:
    """Build the generator task prompt for one iteration."""
    if iteration == 1:
        return build_initial_generator_prompt(
            repo_context=repo_context,
            user_prompt=req.prompt,
        )

    return build_retry_generator_prompt(
        repo_context=repo_context,
        user_prompt=req.prompt,
        previous_generator_output=previous_generator_output,
        reviewer_feedback=reviewer_feedback,
    )


def is_iteration_approved(reviewer_results: list[ReviewerResult]) -> bool:
    """Return whether every reviewer approved the current iteration."""
    return all(result.approved for result in reviewer_results)
