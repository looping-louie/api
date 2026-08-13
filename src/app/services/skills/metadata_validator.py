"""Validation rules for structured skill metadata."""

from collections.abc import Mapping, Sequence

from src.app.catalogs.skills import SkillCategory


STRICTNESS_PHASES: frozenset[str] = frozenset(
    {
        "prototype",
        "mvp",
        "production",
    }
)


class SkillValidationError(Exception):
    """Raised when skill-specific metadata is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        """Describe the invalid metadata field and reason."""

        super().__init__(f"Invalid skill field '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


def validate_skill_metadata(metadata: Mapping[str, object]) -> None:
    """Validate supported structured skill metadata fields."""

    applies_when = metadata.get("applies_when")
    if applies_when is not None:
        _validate_applies_when(applies_when)

    default_strictness = metadata.get("default_strictness")
    if default_strictness is not None:
        _validate_default_strictness(default_strictness)

    category = metadata.get("category")
    if category is not None:
        _validate_category(category)


def _validate_category(value: object) -> None:
    """Require one category from the stable company-area taxonomy."""

    if not isinstance(value, str):
        raise SkillValidationError(
            field_name="metadata.category",
            message="must be a supported skill category",
        )

    try:
        SkillCategory(value)
    except ValueError as exc:
        raise SkillValidationError(
            field_name="metadata.category",
            message="must be a supported skill category",
        ) from exc


def _validate_applies_when(value: object) -> None:
    """Require unique, non-empty applicability descriptions."""

    if not _is_sequence(value):
        raise SkillValidationError(
            field_name="metadata.applies_when",
            message="must be a list of strings",
        )

    normalized_values: list[str] = []
    seen: set[str] = set()

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise SkillValidationError(
                field_name="metadata.applies_when",
                message="must contain only non-empty strings",
            )

        normalized = item.strip()
        comparison_key = normalized.casefold()
        if comparison_key in seen:
            raise SkillValidationError(
                field_name="metadata.applies_when",
                message=f"contains duplicate value '{normalized}'",
            )

        seen.add(comparison_key)
        normalized_values.append(normalized)

    if not normalized_values:
        raise SkillValidationError(
            field_name="metadata.applies_when",
            message="must contain at least one value",
        )


def _validate_default_strictness(value: object) -> None:
    """Require supported project phases with integer percentages."""

    if not isinstance(value, Mapping):
        raise SkillValidationError(
            field_name="metadata.default_strictness",
            message="must be an object",
        )

    unknown_phases = set(value) - STRICTNESS_PHASES
    if unknown_phases:
        phases = ", ".join(sorted(str(phase) for phase in unknown_phases))
        raise SkillValidationError(
            field_name="metadata.default_strictness",
            message=f"contains unsupported phases: {phases}",
        )

    for phase, strictness in value.items():
        _validate_strictness_value(
            phase=str(phase),
            value=strictness,
        )


def _validate_strictness_value(*, phase: str, value: object) -> None:
    """Require an integer strictness value between zero and one hundred."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise SkillValidationError(
            field_name=f"metadata.default_strictness.{phase}",
            message="must be an integer between 0 and 100",
        )

    if value < 0 or value > 100:
        raise SkillValidationError(
            field_name=f"metadata.default_strictness.{phase}",
            message="must be between 0 and 100",
        )


def _is_sequence(value: object) -> bool:
    """Return whether a value is a non-text sequence."""

    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )
