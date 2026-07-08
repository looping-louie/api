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
VALID_AGENT_ROLES = {"generator", "reviewer"}
PROJECT_PHASES = ("prototype", "mvp", "production")


# TODO:
# Cache loaded skills in memory.
# Skills are immutable during one process lifetime and are currently
# read from disk on every model invocation.
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

    Registry metadata determines when a skill applies, which agent roles may
    use it, and the default reviewer strictness for each project phase.
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

        # Fail during startup or planning rather than during a model call.
        load_skill(skill_id)
        seen_ids.add(skill_id)

    return data


def _validate_registry_entry(entry: Any) -> None:
    """Validate one skill registry entry."""
    if not isinstance(entry, dict):
        raise RuntimeError("Each skill registry entry must be an object")

    required_fields = {
        "id",
        "description",
        "applies_when",
        "applies_to",
        "reviewer_default_strictness",
    }
    missing = required_fields - entry.keys()

    if missing:
        raise RuntimeError(
            f"Skill registry entry is missing: {sorted(missing)}"
        )

    skill_id = entry["id"]

    if not isinstance(skill_id, str) or not skill_id.strip():
        raise RuntimeError("Skill id must be a non-empty string")

    _validate_non_empty_string(
        value=entry["description"],
        field="description",
        skill_id=skill_id,
    )
    _validate_string_list(
        value=entry["applies_when"],
        field="applies_when",
        skill_id=skill_id,
        allow_empty=False,
    )
    _validate_agent_roles(
        value=entry["applies_to"],
        skill_id=skill_id,
    )
    _validate_reviewer_strictness(
        value=entry["reviewer_default_strictness"],
        skill_id=skill_id,
    )


def _validate_non_empty_string(
    *,
    value: Any,
    field: str,
    skill_id: str,
) -> None:
    """Require a non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"Skill '{skill_id}' {field} must be a non-empty string"
        )


def _validate_string_list(
    *,
    value: Any,
    field: str,
    skill_id: str,
    allow_empty: bool,
) -> None:
    """Require a list containing only non-empty strings."""
    if not isinstance(value, list):
        raise RuntimeError(
            f"Skill '{skill_id}' {field} must be a list"
        )

    if not allow_empty and not value:
        raise RuntimeError(
            f"Skill '{skill_id}' {field} must not be empty"
        )

    if any(
        not isinstance(item, str) or not item.strip()
        for item in value
    ):
        raise RuntimeError(
            f"Skill '{skill_id}' {field} must contain "
            "non-empty strings"
        )


def _validate_agent_roles(*, value: Any, skill_id: str) -> None:
    """Validate the agent roles allowed to consume one skill."""
    _validate_string_list(
        value=value,
        field="applies_to",
        skill_id=skill_id,
        allow_empty=False,
    )

    invalid_roles = set(value) - VALID_AGENT_ROLES

    if invalid_roles:
        raise RuntimeError(
            f"Skill '{skill_id}' applies_to contains invalid roles: "
            f"{sorted(invalid_roles)}"
        )


def _validate_reviewer_strictness(
    *,
    value: Any,
    skill_id: str,
) -> None:
    """Validate reviewer strictness defaults for every project phase."""
    if not isinstance(value, dict):
        raise RuntimeError(
            f"Skill '{skill_id}' reviewer_default_strictness "
            "must be an object"
        )

    for phase in PROJECT_PHASES:
        phase_value = value.get(phase)

        if (
            not isinstance(phase_value, int)
            or not 0 <= phase_value <= 100
        ):
            raise RuntimeError(
                f"Skill '{skill_id}' requires a valid "
                f"reviewer_default_strictness.{phase}"
            )
