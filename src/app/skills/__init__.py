"""Temporary compatibility wrapper for the relocated skill catalog.

Deprecated: runtime callers still use legacy skill keys during the catalog-to-
SQL transition. New code must import ``src.app.catalogs.skills`` directly.
Remove this wrapper once execution resolves instructions from SQL.
"""

from typing import Any

from src.app.catalogs.skills import (
    load_skill_catalog,
    load_skill_content,
)


def load_skill(skill_name: str) -> str:
    """Load a skill by stable ID or its temporary legacy key."""

    return load_skill_content(skill_name)


def load_skill_registry() -> list[dict[str, Any]]:
    """Return the legacy registry shape expected by current planners."""

    return [
        {
            "id": entry["key"],
            "description": entry["description"],
            "applies_when": list(entry["applies_when"]),
            "applies_to": list(entry["applies_to"]),
            "reviewer_default_strictness": dict(
                entry["reviewer_default_strictness"]
            ),
        }
        for entry in load_skill_catalog()
    ]


__all__ = [
    "load_skill",
    "load_skill_registry",
]
