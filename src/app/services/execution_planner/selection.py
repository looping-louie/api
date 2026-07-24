"""Persona, skill, and fallback selection helpers."""

from typing import Any

from src.app.schemas import ReviewerAssignment

from .constants import (
    DEFAULT_PHASE,
    STRICTNESS_DEVIATION,
    VALID_PHASES,
)


def best_persona_match(
    *,
    reviewer_indexes: list[int],
    reviewers: list[ReviewerAssignment],
    skill_id: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> int | None:
    """Select a reviewer whose persona is associated with the skill."""

    if not reviewer_indexes:
        return None

    associated = [
        index
        for index in reviewer_indexes
        if skill_id
        in personas_by_id[reviewers[index].persona]["skills"]
    ]
    return associated[0] if associated else reviewer_indexes[0]


def find_reviewer_with_replaceable_skill(
    *,
    reviewers: list[ReviewerAssignment],
    skill_id: str,
    required_skills: set[str],
    personas_by_id: dict[str, dict[str, Any]],
) -> int | None:
    """Find a reviewer containing at least one optional skill."""

    candidates = [
        index
        for index, reviewer in enumerate(reviewers)
        if any(
            current_skill not in required_skills
            for current_skill in reviewer.skills
        )
    ]
    return best_persona_match(
        reviewer_indexes=candidates,
        reviewers=reviewers,
        skill_id=skill_id,
        personas_by_id=personas_by_id,
    )


def select_persona_for_skill(
    *,
    skill_id: str,
    role: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> str:
    """Select a deterministic role-compatible persona for one skill."""

    compatible = [
        persona_id
        for persona_id, entry in personas_by_id.items()
        if supports_role(entry, role)
    ]
    associated = [
        persona_id
        for persona_id in compatible
        if skill_id in personas_by_id[persona_id]["skills"]
    ]

    if associated:
        return associated[0]

    defaults = [
        persona_id
        for persona_id in compatible
        if role in personas_by_id[persona_id]["default_for"]
    ]

    if defaults:
        return defaults[0]

    if compatible:
        return compatible[0]

    raise RuntimeError(f"No persona supports role: {role}")


def normalise_persona_id(
    *,
    persona_id: Any,
    role: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> str:
    """Return a valid persona ID or a deterministic fallback."""

    if isinstance(persona_id, str):
        entry = personas_by_id.get(persona_id)
        if supports_role(entry, role):
            return persona_id

    return select_default_persona(
        role=role,
        personas_by_id=personas_by_id,
    )


def select_default_persona(
    *,
    role: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> str:
    """Select the configured default persona for a role."""

    compatible = [
        persona_id
        for persona_id, entry in personas_by_id.items()
        if supports_role(entry, role)
    ]
    defaults = [
        persona_id
        for persona_id in compatible
        if role in personas_by_id[persona_id]["default_for"]
    ]

    if defaults:
        return defaults[0]

    if compatible:
        return compatible[0]

    raise RuntimeError(f"No persona supports role: {role}")


def normalise_skill_ids(
    *,
    raw_skills: Any,
    role: str,
    skills_by_id: dict[str, dict[str, Any]],
    limit: int,
) -> list[str]:
    """Return unique, role-compatible skill IDs."""

    if not isinstance(raw_skills, list):
        return []

    normalised = []

    for skill_id in raw_skills:
        if not isinstance(skill_id, str):
            continue
        if skill_id in normalised:
            continue
        if not supports_role(skills_by_id.get(skill_id), role):
            continue

        normalised.append(skill_id)

        if len(normalised) == limit:
            break

    return normalised


def default_strictness(
    *,
    skill_ids: list[str],
    phase: str,
    skills_by_id: dict[str, dict[str, Any]],
) -> int:
    """Use the strictest skill default in one reviewer assignment."""

    defaults = [
        skills_by_id[skill_id]["reviewer_default_strictness"][phase]
        for skill_id in skill_ids
    ]
    return max(defaults)


def normalise_strictness(*, value: Any, default: int) -> int:
    """Clamp planner strictness near the registry default."""

    if not isinstance(value, int):
        value = default

    lower_bound = max(0, default - STRICTNESS_DEVIATION)
    upper_bound = min(100, default + STRICTNESS_DEVIATION)
    return max(lower_bound, min(upper_bound, value))


def default_reviewer_focus(
    *,
    persona_id: str,
    skill_ids: list[str],
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> str:
    """Build a useful fallback focus from persona and skill metadata."""

    skill_descriptions = " ".join(
        skills_by_id[skill_id]["description"]
        for skill_id in skill_ids
    )
    return (
        f'{personas_by_id[persona_id]["description"]} '
        f"Apply these skills: {skill_descriptions}"
    )


def normalise_phase(value: Any) -> str:
    """Return a supported project phase."""

    return value if value in VALID_PHASES else DEFAULT_PHASE


def normalise_text(value: Any, *, fallback: str) -> str:
    """Return stripped planner text or a local fallback."""

    if isinstance(value, str) and value.strip():
        return value.strip()

    return fallback


def supports_role(entry: dict[str, Any] | None, role: str) -> bool:
    """Return whether one registry entry supports the requested role."""

    return bool(entry and role in entry.get("applies_to", []))
