"""Registry and caller-input validation for execution planning."""

from typing import Any

from .constants import (
    MAX_SELECTED_REVIEWERS,
    MAX_SKILLS_PER_REVIEWER,
    VALID_AGENT_ROLES,
    VALID_PHASES,
)
from .selection import supports_role


def validate_required_skills(
    *,
    required_skills: list[str],
    skills_by_id: dict[str, dict[str, Any]],
) -> None:
    """Validate requested reviewer skills and planner capacity."""

    unknown = set(required_skills) - skills_by_id.keys()

    if unknown:
        raise ValueError(
            "Required skills are not available for execution: "
            f"{sorted(unknown)}"
        )

    incompatible = [
        skill_id
        for skill_id in required_skills
        if not supports_role(skills_by_id[skill_id], "reviewer")
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


def validate_generator_persona(
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

    if not supports_role(
        personas_by_id[generator_persona],
        "generator",
    ):
        raise ValueError(
            f"Persona cannot be used as generator: {generator_persona}"
        )


def validate_skill_registry(
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


def validate_persona_registry(
    *,
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> None:
    """Validate persona registry fields and skill references."""

    for persona_id, entry in personas_by_id.items():
        _require_text(entry, "description", "persona", persona_id)
        _require_string_list(entry, "applies_when", "persona", persona_id)
        _require_string_list(entry, "skills", "persona", persona_id)
        _require_string_list(entry, "default_for", "persona", persona_id)
        _require_roles(entry, "persona", persona_id)

        unknown = set(entry["skills"]) - skills_by_id.keys()
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


def index_registry(
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


def unique_strings(values: list[str]) -> list[str]:
    """Preserve order while removing duplicate strings."""

    return list(dict.fromkeys(values))


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
