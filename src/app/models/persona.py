"""Domain models for personas and their skill associations."""

from dataclasses import dataclass

from src.app.models.instruction import (
    AvailableInstructionDocument,
    InstructionDocument,
)


@dataclass(frozen=True, slots=True)
class PersonaDocument(InstructionDocument):
    """Custom persona document with its associated skills."""

    model: str | None = None
    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AvailablePersonaDocument(AvailableInstructionDocument):
    """Workspace-visible persona document with associated skills."""

    model: str | None = None
    skill_ids: tuple[str, ...] = ()
