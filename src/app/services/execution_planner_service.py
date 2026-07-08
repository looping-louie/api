"""
Build the execution plan for one task.

The planner selects one generator persona and a minimal set of reviewer
assignments. Every assignment combines a persona with zero or more technical
skills, while local validation prevents invalid or incompatible plans.
"""

from typing import Any

from src.app.personas import load_persona_registry
from src.app.schemas import (
    ExecutionPlan,
    GeneratorAssignment,
    ReviewerAssignment,
)
from src.app.services.llm_service.openai import plan_execution_with_openai
from src.app.skills import load_skill_registry


MAX_SELECTED_REVIEWERS = 3
MAX_GENERATOR_SKILLS = 3
MAX_SKILLS_PER_REVIEWER = 3
STRICTNESS_DEVIATION = 15

DEFAULT_PHASE = "prototype"
VALID_PHASES = {"prototype", "mvp", "production"}
VALID_AGENT_ROLES = {"generator", "reviewer"}


async def create_execution_plan(
    *,
    model: str,
    task_prompt: str,
    project_profile: dict[str, Any],
    constitution: str,
    required_skills: list[str],
    generator_persona: str | None = None,
) -> ExecutionPlan:
    """
    Build and validate a task-specific generator and reviewer configuration.

    Required skills retain their existing meaning: they must be assigned to at
    least one reviewer. The generator persona may be fixed by the caller or
    selected automatically by the planner.
    """
    skill_registry = load_skill_registry()
    persona_registry = load_persona_registry()

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


def _find_reviewer_with_replaceable_skill(
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
    return _best_persona_match(
        reviewer_indexes=candidates,
        reviewers=reviewers,
        skill_id=skill_id,
        personas_by_id=personas_by_id,
    )


def _best_persona_match(
    *,
    reviewer_indexes: list[int],
    reviewers: list[ReviewerAssignment],
    skill_id: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> int | None:
    """Prefer a reviewer whose persona lists the skill as preferred."""
    if not reviewer_indexes:
        return None

    preferred = [
        index
        for index in reviewer_indexes
        if skill_id
        in personas_by_id[reviewers[index].persona]["preferred_skills"]
    ]
    return preferred[0] if preferred else reviewer_indexes[0]


def _select_persona_for_skill(
    *,
    skill_id: str,
    role: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> str:
    """Select a deterministic role-compatible persona for one skill."""
    compatible = [
        persona_id
        for persona_id, entry in personas_by_id.items()
        if _supports_role(entry, role)
    ]
    preferred = [
        persona_id
        for persona_id in compatible
        if skill_id in personas_by_id[persona_id]["preferred_skills"]
    ]

    if preferred:
        return preferred[0]

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


def _normalise_persona_id(
    *,
    persona_id: Any,
    role: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> str:
    """Return a valid persona ID or a deterministic fallback."""
    if isinstance(persona_id, str):
        entry = personas_by_id.get(persona_id)
        if _supports_role(entry, role):
            return persona_id

    return _select_default_persona(
        role=role,
        personas_by_id=personas_by_id,
    )


def _select_default_persona(
    *,
    role: str,
    personas_by_id: dict[str, dict[str, Any]],
) -> str:
    """Select the configured default persona for a role."""
    compatible = [
        persona_id
        for persona_id, entry in personas_by_id.items()
        if _supports_role(entry, role)
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


def _normalise_skill_ids(
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
        if not _supports_role(skills_by_id.get(skill_id), role):
            continue

        normalised.append(skill_id)

        if len(normalised) == limit:
            break

    return normalised


def _default_strictness(
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


def _normalise_strictness(*, value: Any, default: int) -> int:
    """Clamp planner strictness near the registry default."""
    if not isinstance(value, int):
        value = default

    lower_bound = max(0, default - STRICTNESS_DEVIATION)
    upper_bound = min(100, default + STRICTNESS_DEVIATION)
    return max(lower_bound, min(upper_bound, value))


def _default_reviewer_focus(
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


def _normalise_phase(value: Any) -> str:
    """Return a supported project phase."""
    return value if value in VALID_PHASES else DEFAULT_PHASE


def _normalise_text(value: Any, *, fallback: str) -> str:
    """Return stripped planner text or a local fallback."""
    if isinstance(value, str) and value.strip():
        return value.strip()

    return fallback


def _validate_required_skills(
    *,
    required_skills: list[str],
    skills_by_id: dict[str, dict[str, Any]],
) -> None:
    """Validate requested reviewer skills and planner capacity."""
    unknown = set(required_skills) - skills_by_id.keys()

    if unknown:
        raise ValueError(
            "Required skills are not present in registry.json: "
            f"{sorted(unknown)}"
        )

    incompatible = [
        skill_id
        for skill_id in required_skills
        if not _supports_role(skills_by_id[skill_id], "reviewer")
    ]

    if incompatible:
        raise ValueError(
            "Required skills cannot be assigned to reviewers: "
            f"{sorted(incompatible)}"
        )

    capacity = MAX_SELECTED_REVIEWERS * MAX_SKILLS_PER_REVIEWER

    if len(required_skills) > capacity:
        raise ValueError(
            f"Required skills exceed reviewer capacity of {capacity}"
        )


def _validate_generator_persona(
    *,
    generator_persona: str | None,
    personas_by_id: dict[str, dict[str, Any]],
) -> None:
    """Validate an optional caller-selected generator persona."""
    if generator_persona is None:
        return

    if generator_persona not in personas_by_id:
        raise ValueError(
            f"Unknown generator persona: {generator_persona}"
        )

    if not _supports_role(
        personas_by_id[generator_persona],
        "generator",
    ):
        raise ValueError(
            f"Persona cannot be used as generator: {generator_persona}"
        )


def _validate_skill_registry(
    skills_by_id: dict[str, dict[str, Any]],
) -> None:
    """Validate skill registry fields used by execution planning."""
    for skill_id, entry in skills_by_id.items():
        _require_text(entry, "description", "skill", skill_id)
        _require_string_list(entry, "applies_when", "skill", skill_id)
        _require_roles(entry, "skill", skill_id)

        strictness = entry.get("reviewer_default_strictness")
        if not isinstance(strictness, dict):
            raise ValueError(
                f"Skill '{skill_id}' has invalid reviewer defaults"
            )

        _validate_phase_defaults(
            skill_id=skill_id,
            strictness=strictness,
        )


def _validate_persona_registry(
    *,
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> None:
    """Validate persona registry fields and skill references."""
    for persona_id, entry in personas_by_id.items():
        _require_text(entry, "description", "persona", persona_id)
        _require_string_list(entry, "applies_when", "persona", persona_id)
        _require_string_list(entry, "preferred_skills", "persona", persona_id)
        _require_string_list(entry, "default_for", "persona", persona_id)
        _require_roles(entry, "persona", persona_id)

        unknown = set(entry["preferred_skills"]) - skills_by_id.keys()
        if unknown:
            raise ValueError(
                f"Persona '{persona_id}' references unknown skills: "
                f"{sorted(unknown)}"
            )

        invalid_defaults = set(entry["default_for"]) - VALID_AGENT_ROLES
        if invalid_defaults:
            raise ValueError(
                f"Persona '{persona_id}' has invalid default roles: "
                f"{sorted(invalid_defaults)}"
            )

        unsupported_defaults = (
            set(entry["default_for"]) - set(entry["applies_to"])
        )
        if unsupported_defaults:
            raise ValueError(
                f"Persona '{persona_id}' defaults unsupported roles: "
                f"{sorted(unsupported_defaults)}"
            )


def _validate_phase_defaults(
    *,
    skill_id: str,
    strictness: dict[str, Any],
) -> None:
    """Validate reviewer strictness for every project phase."""
    missing = VALID_PHASES - strictness.keys()

    if missing:
        raise ValueError(
            f"Skill '{skill_id}' misses strictness phases: "
            f"{sorted(missing)}"
        )

    invalid = [
        phase
        for phase in VALID_PHASES
        if not isinstance(strictness[phase], int)
        or not 0 <= strictness[phase] <= 100
    ]

    if invalid:
        raise ValueError(
            f"Skill '{skill_id}' has invalid strictness phases: "
            f"{sorted(invalid)}"
        )


def _require_roles(
    entry: dict[str, Any],
    entry_type: str,
    entry_id: str,
) -> None:
    """Validate role compatibility metadata."""
    _require_string_list(entry, "applies_to", entry_type, entry_id)
    invalid = set(entry["applies_to"]) - VALID_AGENT_ROLES

    if invalid:
        raise ValueError(
            f"{entry_type.title()} '{entry_id}' has invalid roles: "
            f"{sorted(invalid)}"
        )

    if not entry["applies_to"]:
        raise ValueError(
            f"{entry_type.title()} '{entry_id}' supports no roles"
        )


def _require_text(
    entry: dict[str, Any],
    field: str,
    entry_type: str,
    entry_id: str,
) -> None:
    """Require a non-empty string registry field."""
    value = entry.get(field)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{entry_type.title()} '{entry_id}' has invalid '{field}'"
        )


def _require_string_list(
    entry: dict[str, Any],
    field: str,
    entry_type: str,
    entry_id: str,
) -> None:
    """Require a list containing only non-empty strings."""
    value = entry.get(field)

    if not isinstance(value, list):
        raise ValueError(
            f"{entry_type.title()} '{entry_id}' has invalid '{field}'"
        )

    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(
            f"{entry_type.title()} '{entry_id}' has invalid '{field}'"
        )


def _index_registry(
    registry: list[dict[str, Any]],
    entry_type: str,
) -> dict[str, dict[str, Any]]:
    """Index registry entries and reject missing or duplicate IDs."""
    indexed = {}

    for entry in registry:
        entry_id = entry.get("id")

        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValueError(
                f"{entry_type.title()} registry contains an invalid ID"
            )

        if entry_id in indexed:
            raise ValueError(
                f"Duplicate {entry_type} registry ID: {entry_id}"
            )

        indexed[entry_id] = entry

    return indexed


def _supports_role(entry: dict[str, Any] | None, role: str) -> bool:
    """Return whether one registry entry supports the requested role."""
    return bool(entry and role in entry.get("applies_to", []))


def _unique_strings(values: list[str]) -> list[str]:
    """Preserve order while removing duplicate strings."""
    return list(dict.fromkeys(values))
