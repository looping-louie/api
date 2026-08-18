"""Application input types and errors for loop operations."""

from __future__ import annotations

from dataclasses import dataclass

from src.app.models.loop import (
    LoopOutputContract,
    LoopStopConditions,
)


@dataclass(frozen=True, slots=True)
class LoopAgentInput:
    """Agent values accepted by create and patch operations."""

    model_id: str | None
    persona_id: str
    role: str
    id: str | None = None


@dataclass(frozen=True, slots=True)
class LoopCreate:
    """User-managed values required to create a loop."""

    title: str
    description: str
    flow: str
    stop_conditions: LoopStopConditions
    agents: tuple[LoopAgentInput, ...]
    output_contract: LoopOutputContract


@dataclass(frozen=True, slots=True)
class LoopPatch:
    """Partial loop changes with explicit supplied-field tracking."""

    provided_fields: frozenset[str]
    title: str | None = None
    description: str | None = None
    flow: str | None = None
    status: str | None = None
    stop_conditions: LoopStopConditions | None = None
    agents: tuple[LoopAgentInput, ...] | None = None
    output_contract: LoopOutputContract | None = None


class LoopServiceError(Exception):
    """Base error raised by loop operations."""


class LoopValidationError(LoopServiceError):
    """Raised when loop-specific data is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        """Store a field-specific validation failure."""

        super().__init__(f"Invalid loop field '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class LoopNotFoundError(LoopServiceError):
    """Raised when a loop or retained changelog cannot be found."""

    def __init__(self, *, loop_id: str) -> None:
        """Store the missing loop identifier."""

        super().__init__(f"Loop '{loop_id}' was not found.")
        self.loop_id = loop_id


class ArchivedLoopImmutableError(LoopServiceError):
    """Raised when an archived loop receives a non-reactivation change."""

    def __init__(self, *, loop_id: str) -> None:
        """Store the immutable archived loop identifier."""

        super().__init__(
            f"Archived loop '{loop_id}' can only be reactivated."
        )
        self.loop_id = loop_id
