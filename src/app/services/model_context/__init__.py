"""Build generator and reviewer prompt contexts."""

from src.app.services.llm_service.prompts import render_prompt

# TODO:
# Split prompts into stable and dynamic sections so providers supporting
# prompt caching can reuse the repository context across iterations.
def build_initial_generator_prompt(
    repo_context: str,
    user_prompt: str,
) -> str:
    """
    Build the generator prompt for the first iteration.

    The provider-level system prompt defines the required output format. This
    prompt supplies the repository context and the requested development task.
    """
    init_prompt = render_prompt(
        "generator_input.md",
        repo_context=repo_context,
        user_prompt=user_prompt
    )
    return init_prompt


def build_retry_generator_prompt(
    repo_context: str,
    user_prompt: str,
    previous_generator_output: str,
    reviewer_feedback: str,
) -> str:
    """
    Build the generator prompt for a retry iteration.

    Includes the original repository context, the requested task, the previous
    generator response and the feedback that caused the iteration to fail.
    """
    retry_prompt = render_prompt(
        "generator_retry.md",
        repo_context=repo_context,
        user_prompt=user_prompt,
        previous_generator_output=previous_generator_output,
        reviewer_feedback=reviewer_feedback
    )
    return retry_prompt


# TODO:
# Support multimodal reviewer inputs such as screenshots, diagrams and other
# execution artefacts.
def build_reviewer_input(
    user_prompt: str,
    final_diff: str,
    changed_file_contents: str,
) -> str:
    """
    Build the candidate-change context sent to reviewer models.

    Reviewers receive the original task, the Git diff and the full contents of
    every changed file.

    Args:
        user_prompt:
            Original development task.

        final_diff:
            Git diff generated from the worktree changes.

        changed_file_contents:
            Full resulting contents of the changed files.

    Returns:
        Complete reviewer input.
    """
    input_prompt = render_prompt(
        "reviewer_input.md",
        user_prompt=user_prompt,
        final_diff=final_diff,
        changed_file_contents=changed_file_contents
    )
    return input_prompt
