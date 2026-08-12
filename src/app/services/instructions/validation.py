"""Normalization and validation rules for instruction resources."""

from __future__ import annotations

from copy import deepcopy

from .types import (
    InstructionCreate,
    InstructionUpdate,
    InstructionValidationError,
    SUPPORTED_INSTRUCTION_TYPES,
    InvalidInstructionTypeError,
)


def require_instruction_type(instruction_type: str) -> None:
    """Require one supported instruction type."""

    if instruction_type not in SUPPORTED_INSTRUCTION_TYPES:
        raise InvalidInstructionTypeError(instruction_type)


def require_text(value: str, field_name: str) -> str:
    """Return stripped non-empty text."""

    normalized = value.strip()

    if not normalized:
        raise InstructionValidationError(
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


def normalize_create(payload: InstructionCreate) -> InstructionCreate:
    """Normalize and validate create values."""

    return InstructionCreate(
        name=require_text(payload.name, "name"),
        description=normalize_description(payload.description),
        instructions=require_text(payload.instructions, "instructions"),
        metadata=deepcopy(dict(payload.metadata)),
    )


def normalize_update(payload: InstructionUpdate) -> InstructionUpdate:
    """Normalize and validate partial update values."""

    if payload.expected_version < 1:
        raise InstructionValidationError(
            field_name="expected_version",
            message="must be greater than zero",
        )

    return InstructionUpdate(
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
