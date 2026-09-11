"""Persona domain contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from ..persona_skills import (
    AvailableDefinitionDocument,
    AvailableDefinitionSummary,
    DefinitionCreate,
    DefinitionDocument,
    DefinitionUpdate,
)


@dataclass(frozen=True, slots=True)
class PersonaCreate(DefinitionCreate):
    """Content and associations required to create a persona."""

    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PersonaUpdate(DefinitionUpdate):
    """Partial persona content and association changes."""

    skill_ids: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class PersonaDocument(DefinitionDocument):
    """Custom persona document with its associated skills."""

    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AvailablePersonaDocument(AvailableDefinitionDocument):
    """Project-visible persona document with associated skills."""

    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AvailablePersonaSummary(AvailableDefinitionSummary):
    """Project-visible persona summary."""


PersonaBaseDocument = DefinitionDocument | AvailableDefinitionDocument
PersonaResultDocument = PersonaDocument | AvailablePersonaDocument
PersonaSummaryDocument = AvailablePersonaSummary
DocumentType = TypeVar("DocumentType", bound=PersonaBaseDocument)


class PersonaSkillRepository(Protocol):
    """Persistence contract for persona-skill associations."""

    async def list_for_persona(self, *, persona_id: str) -> tuple[str, ...]:
        """Return associated skills in their declared order."""
        raise NotImplementedError

    async def replace_for_persona(
        self,
        *,
        persona_id: str,
        skill_ids: Sequence[str],
    ) -> None:
        """Replace every skill associated with a persona."""
        raise NotImplementedError






