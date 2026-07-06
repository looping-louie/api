"""
Skill loader.

Skills are stored as Markdown documents with YAML front matter under
the skills/ directory.

The loader searches recursively so skills can be organised by category,
for example:

skills/
    code_review/
    security/
    seo/
    accessibility/

Skill names must be globally unique regardless of directory.
"""

import json
from pathlib import Path
from typing import Any

SKILLS_DIR = Path(__file__).parent
REGISTRY_PATH = SKILLS_DIR / "registry.json"

# TODO:
# Cache loaded skills in memory.
# Skills are immutable during one process lifetime and are currently
# read from disk on every reviewer invocation.
def load_skill(skill_name: str) -> str:
    """
    Load a skill by its logical name.

    The search is recursive under the skills directory.

    Raises:
        ValueError:
            - if the skill does not exist.
            - if multiple skills with the same name exist.

    Returns:
        The complete Markdown document, including YAML front matter.
    """
    matches = list(SKILLS_DIR.rglob(f"{skill_name}.md"))

    if not matches:
        raise ValueError(f"Unknown skill: {skill_name}")

    if len(matches) > 1:
        locations = "\n".join(
            str(path.relative_to(SKILLS_DIR))
            for path in matches
        )
        raise ValueError(
            f"Multiple skills named '{skill_name}' found:\n{locations}"
        )

    return matches[0].read_text(encoding="utf-8")


def load_skill_registry() -> list[dict[str, Any]]:
    """
    Load and validate the skill registry.
    """
    if not REGISTRY_PATH.exists():
        raise RuntimeError(
            f"Skill registry does not exist: {REGISTRY_PATH}"
        )

    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid skill registry JSON: {exc}"
        ) from exc

    if not isinstance(data, list):
        raise RuntimeError("Skill registry must contain a JSON array")

    seen_ids: set[str] = set()

    for entry in data:
        _validate_registry_entry(entry)

        skill_id = entry["id"]

        if skill_id in seen_ids:
            raise RuntimeError(
                f"Duplicate skill registry id: {skill_id}"
            )

        # Fail on startup/planning rather than during a reviewer call.
        load_skill(skill_id)
        seen_ids.add(skill_id)

    return data


def _validate_registry_entry(entry: Any) -> None:
    if not isinstance(entry, dict):
        raise RuntimeError("Each skill registry entry must be an object")

    required_fields = {
        "id",
        "description",
        "applies_when",
        "default_strictness",
    }

    missing = required_fields - entry.keys()

    if missing:
        raise RuntimeError(
            f"Skill registry entry is missing: {sorted(missing)}"
        )

    if not isinstance(entry["id"], str) or not entry["id"].strip():
        raise RuntimeError("Skill id must be a non-empty string")

    if not isinstance(entry["description"], str):
        raise RuntimeError(
            f"Skill '{entry['id']}' description must be a string"
        )

    if not isinstance(entry["applies_when"], list):
        raise RuntimeError(
            f"Skill '{entry['id']}' applies_when must be a list"
        )

    strictness = entry["default_strictness"]

    if not isinstance(strictness, dict):
        raise RuntimeError(
            f"Skill '{entry['id']}' default_strictness must be an object"
        )

    for phase in ("prototype", "mvp", "production"):
        value = strictness.get(phase)

        if not isinstance(value, int) or not 0 <= value <= 100:
            raise RuntimeError(
                f"Skill '{entry['id']}' requires a valid "
                f"default_strictness.{phase}"
            )
