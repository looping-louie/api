"""Prompt assembly helpers shared across services.

Transitional location: moved out of harness so instructions can remain in API
when harness execution migrates to CLI.
"""

from src.app.personas import load_persona
from src.app.skills import load_skill


MAX_GENERATOR_SKILLS = 1


def build_assignment_instructions(
    *,
    role: str,
    persona_id: str,
    skill_ids: list[str],
    focus: str,
) -> str:
    """
    Build provider-agnostic instructions from one persona and its skills.

    Loaders own filesystem lookup and registry validation. Callers only
    combine persona and skill content for the model call.
    """
    effective_skill_ids = (
        skill_ids[:MAX_GENERATOR_SKILLS]
        if role == 'generator'
        else skill_ids
    )
    persona_content = load_persona(persona_id).strip()
    skill_contents = [
        load_skill(skill_id).strip()
        for skill_id in effective_skill_ids
    ]

    sections = [
        f'# {role.title()} assignment',
        '## Persona',
        persona_content,
    ]

    if skill_contents:
        sections.extend(
            [
                '## Assigned skills',
                '\n\n---\n\n'.join(skill_contents),
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
