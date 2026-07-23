"""Pure prompt assembly helpers shared across execution services."""

from collections.abc import Sequence


MAX_GENERATOR_SKILLS = 1


def build_assignment_instructions(
    *,
    role: str,
    persona_content: str,
    skill_contents: Sequence[str],
    focus: str,
) -> str:
    """Build provider-agnostic instructions from already-resolved content."""

    effective_skill_contents = (
        skill_contents[:MAX_GENERATOR_SKILLS]
        if role == 'generator'
        else skill_contents
    )
    normalized_skills = [
        content.strip()
        for content in effective_skill_contents
        if content.strip()
    ]

    sections = [
        f'# {role.title()} assignment',
        '## Persona',
        persona_content.strip(),
    ]

    if normalized_skills:
        sections.extend(
            [
                '## Assigned skills',
                '\n\n---\n\n'.join(normalized_skills),
            ]
        )

    sections.extend(
        [
            '## Task-specific focus',
            focus.strip(),
        ]
    )

    return '\n\n'.join(sections)


def combine_generator_prompt(
    *,
    assignment_instructions: str,
    task_prompt: str,
) -> str:
    """Place assignment context before the existing generator contract."""
    return (
        f'{assignment_instructions}\n\n'
        '# Execution instructions\n\n'
        f'{task_prompt}'
    )


__all__ = [
    'build_assignment_instructions',
    'combine_generator_prompt',
]
