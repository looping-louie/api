"""Persona domain contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from ..persona_skills import (
    AvailableInstructionDocument,
    AvailableInstructionSummary,
    DefinitionCreate,
    InstructionDocument,
    DefinitionUpdate,
)


@dataclass(frozen=True, slots=True)
class PersonaCreate(DefinitionCreate):
    """Content and associations required to create a persona."""

    linked_service_selection: PersonaLinkedServiceSelection | None = None
    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PersonaUpdate(DefinitionUpdate):
    """Partial persona content and association changes."""

    linked_service_selection: PersonaLinkedServiceSelection | None = None
    linked_service_selection_supplied: bool = False
    skill_ids: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class PersonaLinkedServiceSelection:
    """A persona's model selection through one linked service."""

    linked_service_id: str
    model_id: str


@dataclass(frozen=True, slots=True)
class PersonaDocument(InstructionDocument):
    """Custom persona document with its associated skills."""

    linked_service_selection: PersonaLinkedServiceSelection | None = None
    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AvailablePersonaDocument(AvailableInstructionDocument):
    """Workspace-visible persona document with associated skills."""

    linked_service_selection: PersonaLinkedServiceSelection | None = None
    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AvailablePersonaSummary(AvailableInstructionSummary):
    """Workspace-visible persona summary with its selected model."""

    linked_service_selection: PersonaLinkedServiceSelection | None = None


PersonaBaseDocument = InstructionDocument | AvailableInstructionDocument
PersonaResultDocument = PersonaDocument | AvailablePersonaDocument
PersonaSummaryDocument = AvailablePersonaSummary
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


class PersonaLinkedServiceSelectionRepository(Protocol):
    """Persist workspace-scoped Persona linked-service selections."""

    async def get_for_persona(
        self,
        *,
        workspace_id: str,
        persona_id: str,
    ) -> PersonaLinkedServiceSelection | None:
        """Return the linked-service selection when one exists."""
        ...

    async def replace_for_persona(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        selection: PersonaLinkedServiceSelection,
    ) -> None:
        """Store or remove the optional linked-service selection."""
        ...
