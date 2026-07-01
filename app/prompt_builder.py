def build_initial_generator_prompt(
    repo_context: str,
    user_prompt: str,
) -> str:
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


def build_reviewer_input(
    user_prompt: str,
    final_diff: str,
    changed_file_contents: str,
) -> str:
    return f"""
Original user prompt:

{user_prompt}

Git diff:

{final_diff}

Changed files:

{changed_file_contents}
""".strip()