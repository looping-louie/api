"""Registry preparation and constraint validation for meeting teams."""

from __future__ import annotations

from typing import Any


def index_registry(
    registry: list[dict[str, Any]],
    entry_type: str,
) -> dict[str, dict[str, Any]]:
    """Index registry entries by ID and reject duplicates."""

    indexed: dict[str, dict[str, Any]] = {}

    for entry in registry:
        entry_id = entry.get("id")

        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValueError(
                f"{entry_type.title()} registry contains an invalid id"
            )

        if entry_id in indexed:
            raise ValueError(
                f"Duplicate {entry_type} registry id: {entry_id}"
            )

        indexed[entry_id] = entry

    return indexed


def validate_meeting_constraints(
    *,
    required_personas: list[str],
    required_skills: list[str],
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
    max_people: int,
) -> None:
    """Validate user-supplied persona and skill constraints."""

    unknown_personas = set(required_personas) - personas_by_id.keys()
    unknown_skills = set(required_skills) - skills_by_id.keys()

    if unknown_personas:
        raise ValueError(
            "Required personas are not available for execution: "
            f"{sorted(unknown_personas)}"
        )

    if unknown_skills:
        raise ValueError(
            "Required skills are not available for execution: "
            f"{sorted(unknown_skills)}"
        )

    if len(set(required_personas)) > max_people:
        raise ValueError(
            f"Required personas exceed meeting capacity of {max_people}"
        )


def compact_registry(
    registry: list[dict[str, Any]],
    allowed_fields: set[str],
) -> list[dict[str, Any]]:
    """Reduce registry metadata to planner-relevant fields."""

    return [
        {
            key: value
            for key, value in entry.items()
            if key in allowed_fields
        }
        for entry in registry
    ]
