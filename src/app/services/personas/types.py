"""Persona domain contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from ..instructions import (
    AvailableInstructionDocument,
    InstructionCreate,
    InstructionDocument,
    InstructionUpdate,
)


@dataclass(frozen=True, slots=True)
class PersonaCreate(InstructionCreate):
    """Content and associations required to create a persona."""

    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PersonaUpdate(InstructionUpdate):
    """Partial persona content and association changes."""

    skill_ids: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class PersonaDocument(InstructionDocument):
    """Custom persona document with its associated skills."""

    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AvailablePersonaDocument(AvailableInstructionDocument):
    """Workspace-visible persona document with associated skills."""

    skill_ids: tuple[str, ...] = ()


PersonaBaseDocument = InstructionDocument | AvailableInstructionDocument
PersonaResultDocument = PersonaDocument | AvailablePersonaDocument
DocumentType = TypeVar("DocumentType", bound=PersonaBaseDocument)


class PersonaSkillRepository(Protocol):
    """Persistence contract for persona-skill associations."""

    async def list_for_persona(self, *, persona_id: str) -> tuple[str, ...]:
        """Return associated skills in their declared order."""
        ...

    async def replace_for_persona(
        self,
        *,
        persona_id: str,
        skill_ids: Sequence[str],
    ) -> None:
        """Replace every skill associated with a persona."""
        ...
