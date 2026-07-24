"""
Build the execution plan for one task.

The planner selects one generator persona and a minimal set of reviewer
assignments. Every assignment combines a persona with zero or more technical
skills, while local validation prevents invalid or incompatible plans.
"""

from typing import Any

from src.app.schemas import (
    ExecutionPlan,
    GeneratorAssignment,
    ReviewerAssignment,
)
from src.app.services.llm_service.openai import plan_execution_with_openai

from .constants import (
    MAX_GENERATOR_SKILLS,
    MAX_SELECTED_REVIEWERS,
    MAX_SKILLS_PER_REVIEWER,
)
from .selection import (
    best_persona_match as _best_persona_match,
    default_reviewer_focus as _default_reviewer_focus,
    default_strictness as _default_strictness,
    find_reviewer_with_replaceable_skill as _find_reviewer_with_replaceable_skill,
    normalise_persona_id as _normalise_persona_id,
    normalise_phase as _normalise_phase,
    normalise_skill_ids as _normalise_skill_ids,
    normalise_strictness as _normalise_strictness,
    normalise_text as _normalise_text,
    select_persona_for_skill as _select_persona_for_skill,
    supports_role as _supports_role,
)
from .validation import (
    index_registry as _index_registry,
    unique_strings as _unique_strings,
    validate_generator_persona as _validate_generator_persona,
    validate_persona_registry as _validate_persona_registry,
    validate_required_skills as _validate_required_skills,
    validate_skill_registry as _validate_skill_registry,
)


async def create_execution_plan(
    *,
    model: str,
    task_prompt: str,
    project_profile: dict[str, Any],
    constitution: str,
    required_skills: list[str],
    skill_registry: list[dict[str, Any]],
    persona_registry: list[dict[str, Any]],
    generator_persona: str | None = None,
) -> ExecutionPlan:
    """
    Build and validate a task-specific generator and reviewer configuration.

    Required skills retain their existing meaning: they must be assigned to at
    least one reviewer. The generator persona may be fixed by the caller or
    selected automatically by the planner.
    """
    skills_by_id = _index_registry(skill_registry, "skill")
    personas_by_id = _index_registry(persona_registry, "persona")

    _validate_skill_registry(skills_by_id)
    _validate_persona_registry(
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )

    required_skills = _unique_strings(required_skills)

    _validate_required_skills(
        required_skills=required_skills,
        skills_by_id=skills_by_id,
    )
    _validate_generator_persona(
        generator_persona=generator_persona,
        personas_by_id=personas_by_id,
    )

    raw_plan = await plan_execution_with_openai(
        model=model,
        task_prompt=task_prompt,
        project_profile=project_profile,
        constitution=constitution,
        skill_registry=skill_registry,
        persona_registry=persona_registry,
        required_skills=required_skills,
        generator_persona=generator_persona,
        max_reviewers=MAX_SELECTED_REVIEWERS,
        max_generator_skills=MAX_GENERATOR_SKILLS,
        max_skills_per_reviewer=MAX_SKILLS_PER_REVIEWER,
    )

    return _normalise_execution_plan(
        raw_plan=raw_plan,
        skills_by_id=skills_by_id,
        personas_by_id=personas_by_id,
        required_skills=required_skills,
        generator_persona=generator_persona,
    )


def _normalise_execution_plan(
    *,
    raw_plan: dict[str, Any],
    skills_by_id: dict[str, dict[str, Any]],
    personas_by_id: dict[str, dict[str, Any]],
    required_skills: list[str],
    generator_persona: str | None,
) -> ExecutionPlan:
    """Convert untrusted planner output into a valid execution plan."""
    phase = _normalise_phase(raw_plan.get("phase"))
    reasoning = _normalise_text(
        raw_plan.get("reasoning"),
        fallback="Planner did not provide reasoning.",
    )

    generator = _normalise_generator(
        raw_generator=raw_plan.get("generator"),
        skills_by_id=skills_by_id,
        personas_by_id=personas_by_id,
        generator_persona=generator_persona,
    )

    reviewers = _normalise_reviewers(
        raw_reviewers=raw_plan.get("reviewers"),
        phase=phase,
        skills_by_id=skills_by_id,
        personas_by_id=personas_by_id,
    )
    reviewers = _ensure_required_skills(
        reviewers=reviewers,
        required_skills=required_skills,
        phase=phase,
        skills_by_id=skills_by_id,
        personas_by_id=personas_by_id,
    )

    if not reviewers:
        raise RuntimeError("Execution planner did not select any valid reviewer")

    return ExecutionPlan(
        phase=phase,
        reasoning=reasoning,
        generator=generator,
        reviewers=reviewers,
    )


def _normalise_generator(
    *,
    raw_generator: Any,
    skills_by_id: dict[str, dict[str, Any]],
    personas_by_id: dict[str, dict[str, Any]],
    generator_persona: str | None,
) -> GeneratorAssignment:
    """Normalise the generator assignment."""
    raw_generator = raw_generator if isinstance(raw_generator, dict) else {}

    persona_id = generator_persona or raw_generator.get("persona")
    persona_id = _normalise_persona_id(
        persona_id=persona_id,
        role="generator",
        personas_by_id=personas_by_id,
    )

    skill_ids = _normalise_skill_ids(
        raw_skills=raw_generator.get("skills"),
        role="generator",
        skills_by_id=skills_by_id,
        limit=MAX_GENERATOR_SKILLS,
    )

    focus = _normalise_text(
        raw_generator.get("focus"),
        fallback=personas_by_id[persona_id]["description"],
    )

    return GeneratorAssignment(
        persona=persona_id,
        skills=skill_ids,
        focus=focus,
    )


def _normalise_reviewers(
    *,
    raw_reviewers: Any,
    phase: str,
    skills_by_id: dict[str, dict[str, Any]],
    personas_by_id: dict[str, dict[str, Any]],
) -> list[ReviewerAssignment]:
    """Normalise reviewer assignments and remove duplicate skill ownership."""
    if not isinstance(raw_reviewers, list):
        return []

    reviewers: list[ReviewerAssignment] = []
    assigned_skills: set[str] = set()

    for item in raw_reviewers:
        reviewer = _normalise_reviewer(
            raw_reviewer=item,
            phase=phase,
            skills_by_id=skills_by_id,
            personas_by_id=personas_by_id,
            assigned_skills=assigned_skills,
        )
        if reviewer is None:
            continue

        reviewers.append(reviewer)
        assigned_skills.update(reviewer.skills)

        if len(reviewers) == MAX_SELECTED_REVIEWERS:
            break

    return reviewers


def _normalise_reviewer(
    *,
    raw_reviewer: Any,
    phase: str,
    skills_by_id: dict[str, dict[str, Any]],
    personas_by_id: dict[str, dict[str, Any]],
    assigned_skills: set[str],
) -> ReviewerAssignment | None:
    """Normalise one reviewer assignment."""
    if not isinstance(raw_reviewer, dict):
        return None

    persona_id = raw_reviewer.get("persona")
    if not _supports_role(personas_by_id.get(persona_id), "reviewer"):
        return None

    skill_ids = _normalise_skill_ids(
        raw_skills=raw_reviewer.get("skills"),
        role="reviewer",
        skills_by_id=skills_by_id,
        limit=MAX_SKILLS_PER_REVIEWER,
    )
    skill_ids = [
        skill_id
        for skill_id in skill_ids
        if skill_id not in assigned_skills
    ]

    if not skill_ids:
        return None

    default_strictness = _default_strictness(
        skill_ids=skill_ids,
        phase=phase,
        skills_by_id=skills_by_id,
    )
    strictness = _normalise_strictness(
        value=raw_reviewer.get("strictness"),
        default=default_strictness,
    )
    focus = _normalise_text(
        raw_reviewer.get("focus"),
        fallback=_default_reviewer_focus(
            persona_id=persona_id,
            skill_ids=skill_ids,
            personas_by_id=personas_by_id,
            skills_by_id=skills_by_id,
        ),
    )

    return ReviewerAssignment(
        persona=persona_id,
        skills=skill_ids,
        strictness=strictness,
        focus=focus,
    )


def _ensure_required_skills(
    *,
    reviewers: list[ReviewerAssignment],
    required_skills: list[str],
    phase: str,
    skills_by_id: dict[str, dict[str, Any]],
    personas_by_id: dict[str, dict[str, Any]],
) -> list[ReviewerAssignment]:
    """Guarantee that every required skill belongs to one reviewer."""
    assigned = {
        skill_id
        for reviewer in reviewers
        for skill_id in reviewer.skills
    }

    for skill_id in required_skills:
        if skill_id in assigned:
            continue

        reviewers = _assign_required_skill(
            reviewers=reviewers,
            skill_id=skill_id,
            required_skills=set(required_skills),
            phase=phase,
            skills_by_id=skills_by_id,
            personas_by_id=personas_by_id,
        )
        assigned.add(skill_id)

    return _recalculate_reviewer_strictness(
        reviewers=reviewers,
        phase=phase,
        skills_by_id=skills_by_id,
    )


def _assign_required_skill(
    *,
    reviewers: list[ReviewerAssignment],
    skill_id: str,
    required_skills: set[str],
    phase: str,
    skills_by_id: dict[str, dict[str, Any]],
    personas_by_id: dict[str, dict[str, Any]],
) -> list[ReviewerAssignment]:
    """Add one required skill without exceeding reviewer limits."""
    reviewer_index = _find_reviewer_with_capacity(
        reviewers=reviewers,
        skill_id=skill_id,
        personas_by_id=personas_by_id,
    )
    if reviewer_index is not None:
        return _add_skill_to_reviewer(
            reviewers=reviewers,
            reviewer_index=reviewer_index,
            skill_id=skill_id,
        )

    if len(reviewers) < MAX_SELECTED_REVIEWERS:
        return [
            *reviewers,
            _build_required_reviewer(
                skill_id=skill_id,
                phase=phase,
                skills_by_id=skills_by_id,
                personas_by_id=personas_by_id,
            ),
        ]

    reviewer_index = _find_reviewer_with_replaceable_skill(
        reviewers=reviewers,
        skill_id=skill_id,
        required_skills=required_skills,
        personas_by_id=personas_by_id,
    )
    if reviewer_index is None:
        raise RuntimeError(
            f"Could not assign required skill within planner limits: {skill_id}"
        )

    return _replace_optional_skill(
        reviewers=reviewers,
        reviewer_index=reviewer_index,
        skill_id=skill_id,
        required_skills=required_skills,
    )


def _build_required_reviewer(
    *,
    skill_id: str,
    phase: str,
    skills_by_id: dict[str, dict[str, Any]],
    personas_by_id: dict[str, dict[str, Any]],
) -> ReviewerAssignment:
    """Create a deterministic reviewer for a missing required skill."""
    persona_id = _select_persona_for_skill(
        skill_id=skill_id,
        role="reviewer",
        personas_by_id=personas_by_id,
    )

    return ReviewerAssignment(
        persona=persona_id,
        skills=[skill_id],
        strictness=_default_strictness(
            skill_ids=[skill_id],
            phase=phase,
            skills_by_id=skills_by_id,
        ),
        focus=_default_reviewer_focus(
            persona_id=persona_id,
            skill_ids=[skill_id],
            personas_by_id=personas_by_id,
            skills_by_id=skills_by_id,
        ),
    )


def _add_skill_to_reviewer(
    *,
    reviewers: list[ReviewerAssignment],
    reviewer_index: int,
    skill_id: str,
) -> list[ReviewerAssignment]:
    """Return reviewers with one skill appended to the selected reviewer."""
    reviewer = reviewers[reviewer_index]
    updated = reviewer.model_copy(
        update={"skills": [*reviewer.skills, skill_id]}
    )
    return [
        updated if index == reviewer_index else item
        for index, item in enumerate(reviewers)
    ]


def _replace_optional_skill(
    *,
    reviewers: list[ReviewerAssignment],
    reviewer_index: int,
    skill_id: str,
    required_skills: set[str],
) -> list[ReviewerAssignment]:
    """Replace one non-required skill when all reviewer slots are full."""
    reviewer = reviewers[reviewer_index]
    replaceable = next(
        current_skill
        for current_skill in reviewer.skills
        if current_skill not in required_skills
    )
    updated_skills = [
        skill_id if current_skill == replaceable else current_skill
        for current_skill in reviewer.skills
    ]
    updated = reviewer.model_copy(update={"skills": updated_skills})

    return [
        updated if index == reviewer_index else item
        for index, item in enumerate(reviewers)
    ]


def _recalculate_reviewer_strictness(
    *,
    reviewers: list[ReviewerAssignment],
    phase: str,
    skills_by_id: dict[str, dict[str, Any]],
) -> list[ReviewerAssignment]:
    """Clamp strictness against defaults for the final reviewer skill set."""
    normalised = []

    for reviewer in reviewers:
        default = _default_strictness(
            skill_ids=reviewer.skills,
            phase=phase,
            skills_by_id=skills_by_id,
        )
        normalised.append(
            reviewer.model_copy(
                update={
                    "strictness": _normalise_strictness(
                        value=reviewer.strictness,
                        default=default,
                    )
                }
            )
        )

    return normalised


def _find_reviewer_with_capacity(
    *,
    reviewers: list[ReviewerAssignment],
    skill_id: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> int | None:
    """Find the best existing reviewer with room for another skill."""
    candidates = [
        index
        for index, reviewer in enumerate(reviewers)
        if len(reviewer.skills) < MAX_SKILLS_PER_REVIEWER
    ]
    return _best_persona_match(
        reviewer_indexes=candidates,
        reviewers=reviewers,
        skill_id=skill_id,
        personas_by_id=personas_by_id,
    )
