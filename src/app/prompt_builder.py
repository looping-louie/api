"""
Prompt builder.

Constructs every prompt exchanged with generator and reviewer models.

Keeping prompt generation isolated in one module makes prompt engineering
versionable, testable and independent from the orchestration logic.

The runner should never build prompts directly.
"""

# TODO:
# Split prompts into stable and dynamic sections so providers supporting
# prompt caching can reuse the repository context across iterations.
def build_initial_generator_prompt(
    repo_context: str,
    user_prompt: str,
) -> str:
    """
    Build the generator prompt for the first iteration.

    The prompt contains the repository snapshot and the user's requested task.
    """
    return f"""
Repository context:

{repo_context}

User task:

{user_prompt}

Return ONLY JSON file operations.
Do not return a git patch.
""".strip()


def build_retry_generator_prompt(
    repo_context: str,
    user_prompt: str,
    previous_generator_output: str,
    reviewer_feedback: str,
) -> str:
    """
    Build the generator prompt for retry iterations.

    In addition to the repository snapshot and user task, retry prompts include
    the previous generator output and reviewer feedback so the model can refine
    its proposal.
    """
    return f"""
Repository context:

{repo_context}

User task:

{user_prompt}

Previous generator output:

{previous_generator_output}

Reviewer or system feedback:

{reviewer_feedback}

Return corrected JSON file operations only.
""".strip()


# TODO:
# Support multimodal reviewer inputs (screenshots, diagrams and other
# artefacts) in addition to text-based diffs.
def build_reviewer_input(
    user_prompt: str,
    final_diff: str,
    changed_file_contents: str,
) -> str:
    """
    Build the reviewer input.

    Reviewers receive:
    - the original user request;
    - the git diff produced by the generator;
    - the full contents of every changed file.

    This allows skills to review both the change itself and its surrounding
    context.
    """
    return f"""
Original user prompt:

{user_prompt}

Git diff:

{final_diff}

Changed files:

{changed_file_contents}
""".strip()