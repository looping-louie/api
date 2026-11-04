"""Normalization and validation rules for instruction resources."""

from __future__ import annotations

from copy import deepcopy

from .types import (
    DefinitionCreate,
    DefinitionUpdate,
    DefinitionValidationError,
    SUPPORTED_INSTRUCTION_TYPES,
    InvalidDefinitionTypeError,
)


def require_instruction_type(instruction_type: str) -> None:
    """Require one supported instruction type."""

    if instruction_type not in SUPPORTED_INSTRUCTION_TYPES:
        raise InvalidDefinitionTypeError(instruction_type)


def require_text(value: str, field_name: str) -> str:
    """Return stripped non-empty text."""

    normalized = value.strip()

    if not normalized:
        raise DefinitionValidationError(
            field_name=field_name,
            message="must not be empty",
        )

    return normalized


def normalize_description(value: str) -> str:
    """Return stripped description text."""

    return value.strip()


def normalize_search(search: str | None) -> str | None:
    """Return a stripped optional search query."""

    if search is None:
        return None

    normalized = search.strip()
    return normalized or None


def normalize_create(payload: DefinitionCreate) -> DefinitionCreate:
    """Normalize and validate create values."""

    return DefinitionCreate(
        name=require_text(payload.name, "name"),
        description=normalize_description(payload.description),
        instructions=require_text(payload.instructions, "instructions"),
        metadata=deepcopy(dict(payload.metadata)),
    )


def normalize_update(payload: DefinitionUpdate) -> DefinitionUpdate:
    """Normalize and validate partial update values."""

    if payload.expected_version < 1:
        raise DefinitionValidationError(
            field_name="expected_version",
            message="must be greater than zero",
        )

    return DefinitionUpdate(
        expected_version=payload.expected_version,
        name=(
            require_text(payload.name, "name")
            if payload.name is not None
            else None
        ),
        description=(
            normalize_description(payload.description)
            if payload.description is not None
            else None
        ),
        instructions=(
            require_text(payload.instructions, "instructions")
            if payload.instructions is not None
            else None
        ),
        metadata=(
            deepcopy(dict(payload.metadata))
            if payload.metadata is not None
            else None
        ),
    )
