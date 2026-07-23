"""Temporary compatibility wrapper for the relocated persona catalog.

Deprecated: runtime callers still use legacy persona keys during the catalog-
to-SQL transition. New code must import ``src.app.catalogs.personas`` directly.
Remove this wrapper once execution resolves instructions from SQL.
"""

from typing import Any

from src.app.catalogs.personas import (
    load_persona_catalog,
    load_persona_content,
)


def load_persona(persona_name: str) -> str:
    """Load a persona by stable ID or its temporary legacy key."""

    return load_persona_content(persona_name)


def load_persona_registry() -> list[dict[str, Any]]:
    """Return the legacy registry shape expected by current planners."""

    return [
        {
            "id": entry.key,
            "description": entry.description,
            "applies_when": list(entry.metadata.applies_when),
            "applies_to": sorted(
                role.value
                for role in entry.metadata.applies_to
            ),
            "preferred_skills": [
                skill_id.rsplit(":", maxsplit=1)[-1]
                for skill_id in entry.preferred_skill_ids
            ],
            "default_for": sorted(
                role.value
                for role in entry.default_for
            ),
        }
        for entry in load_persona_catalog()
    ]


__all__ = [
    "load_persona",
    "load_persona_registry",
]
