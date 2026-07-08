"""
Persona loader.

Personas are stored as Markdown documents under the personas/ directory.

The loader searches recursively so personas can be organised by category,
for example:

personas/
    product/
    engineering/
    business/
    customer/

Persona names must be globally unique regardless of directory.
"""

import json
from pathlib import Path
from typing import Any


PERSONAS_DIR = Path(__file__).parent
REGISTRY_PATH = PERSONAS_DIR / "registry.json"
VALID_AGENT_ROLES = {"generator", "reviewer"}


# TODO:
# Cache loaded personas in memory.
# Personas are immutable during one process lifetime and are currently
# read from disk on every model invocation.
def load_persona(persona_name: str) -> str:
    """
    Load a persona by its logical name.

    The search is recursive under the personas directory.

    Raises:
        ValueError:
            - if the persona does not exist.
            - if multiple personas with the same name exist.

    Returns:
        The complete Markdown persona document.
    """
    matches = list(PERSONAS_DIR.rglob(f"{persona_name}.md"))

    if not matches:
        raise ValueError(f"Unknown persona: {persona_name}")

    if len(matches) > 1:
        locations = "\n".join(
            str(path.relative_to(PERSONAS_DIR))
            for path in matches
        )
        raise ValueError(
            f"Multiple personas named '{persona_name}' found:\n"
            f"{locations}"
        )

    return matches[0].read_text(encoding="utf-8")


def load_persona_registry() -> list[dict[str, Any]]:
    """
    Load and validate the persona registry.

    Registry metadata determines when a persona is useful, which agent roles
    it may occupy, and which skills naturally complement it.
    """
    if not REGISTRY_PATH.exists():
        raise RuntimeError(
            f"Persona registry does not exist: {REGISTRY_PATH}"
        )

    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid persona registry JSON: {exc}"
        ) from exc

    if not isinstance(data, list):
        raise RuntimeError("Persona registry must contain a JSON array")

    seen_ids: set[str] = set()

    for entry in data:
        _validate_registry_entry(entry)

        persona_id = entry["id"]

        if persona_id in seen_ids:
            raise RuntimeError(
                f"Duplicate persona registry id: {persona_id}"
            )

        # Fail during startup or planning rather than during a model call.
        load_persona(persona_id)
        seen_ids.add(persona_id)

    return data


def _validate_registry_entry(entry: Any) -> None:
    """Validate one persona registry entry."""
    if not isinstance(entry, dict):
        raise RuntimeError(
            "Each persona registry entry must be an object"
        )

    required_fields = {
        "id",
        "description",
        "applies_when",
        "applies_to",
        "preferred_skills",
        "default_for",
    }
    missing = required_fields - entry.keys()

    if missing:
        raise RuntimeError(
            f"Persona registry entry is missing: {sorted(missing)}"
        )

    persona_id = entry["id"]

    if not isinstance(persona_id, str) or not persona_id.strip():
        raise RuntimeError("Persona id must be a non-empty string")

    _validate_non_empty_string(
        value=entry["description"],
        field="description",
        persona_id=persona_id,
    )
    _validate_string_list(
        value=entry["applies_when"],
        field="applies_when",
        persona_id=persona_id,
        allow_empty=False,
    )
    _validate_agent_roles(
        value=entry["applies_to"],
        persona_id=persona_id,
    )
    _validate_string_list(
        value=entry["preferred_skills"],
        field="preferred_skills",
        persona_id=persona_id,
        allow_empty=True,
    )
    _validate_default_roles(
        value=entry["default_for"],
        applies_to=entry["applies_to"],
        persona_id=persona_id,
    )


def _validate_non_empty_string(
    *,
    value: Any,
    field: str,
    persona_id: str,
) -> None:
    """Require a non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"Persona '{persona_id}' {field} must be a non-empty string"
        )


def _validate_string_list(
    *,
    value: Any,
    field: str,
    persona_id: str,
    allow_empty: bool,
) -> None:
    """Require a list containing only non-empty strings."""
    if not isinstance(value, list):
        raise RuntimeError(
            f"Persona '{persona_id}' {field} must be a list"
        )

    if not allow_empty and not value:
        raise RuntimeError(
            f"Persona '{persona_id}' {field} must not be empty"
        )

    if any(
        not isinstance(item, str) or not item.strip()
        for item in value
    ):
        raise RuntimeError(
            f"Persona '{persona_id}' {field} must contain "
            "non-empty strings"
        )


def _validate_agent_roles(*, value: Any, persona_id: str) -> None:
    """Validate the agent roles one persona may occupy."""
    _validate_string_list(
        value=value,
        field="applies_to",
        persona_id=persona_id,
        allow_empty=False,
    )

    invalid_roles = set(value) - VALID_AGENT_ROLES

    if invalid_roles:
        raise RuntimeError(
            f"Persona '{persona_id}' applies_to contains invalid roles: "
            f"{sorted(invalid_roles)}"
        )


def _validate_default_roles(
    *,
    value: Any,
    applies_to: list[str],
    persona_id: str,
) -> None:
    """Validate default roles and ensure the persona supports them."""
    _validate_string_list(
        value=value,
        field="default_for",
        persona_id=persona_id,
        allow_empty=True,
    )

    invalid_roles = set(value) - VALID_AGENT_ROLES

    if invalid_roles:
        raise RuntimeError(
            f"Persona '{persona_id}' default_for contains invalid roles: "
            f"{sorted(invalid_roles)}"
        )

    unsupported_roles = set(value) - set(applies_to)

    if unsupported_roles:
        raise RuntimeError(
            f"Persona '{persona_id}' is default for unsupported roles: "
            f"{sorted(unsupported_roles)}"
        )
