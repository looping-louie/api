"""Workspace-aware application service for persona resources."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from typing import Protocol, TypeVar

from ..shared.instruction import (
    AvailableInstructionDocument,
    AvailableInstructionSummary,
    InstructionCreate,
    InstructionDocument,
    InstructionService,
    InstructionUpdate,
)
from ..shared.tenant import TenantService


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


class PersonaService:
    """Application service for persona operations."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        instruction_service: InstructionService,
        persona_skill_repository: PersonaSkillRepository,
    ) -> None:
        """Initialize workspace resolution and shared instruction behavior."""

        self._tenant_service = tenant_service
        self._instruction_service = instruction_service
        self._persona_skill_repository = persona_skill_repository

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> list[AvailableInstructionSummary]:
        """List personas available in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._instruction_service.list(
            workspace_id=workspace_id,
            instruction_type="persona",
            search=search,
        )

    async def describe(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
        include_deprecated: bool = False,
    ) -> AvailablePersonaDocument:
        """Return a complete persona."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        document = await self._instruction_service.describe(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
            include_deprecated=include_deprecated,
        )
        return await self._with_skill_ids(document)

    async def set_enabled(
        self,
        *,
        user_id: str,
        persona_id: str,
        enabled: bool,
        requested_workspace_id: str | None = None,
    ) -> AvailablePersonaDocument:
        """Set whether a persona is enabled in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        operation = (
            self._instruction_service.enable
            if enabled
            else self._instruction_service.disable
        )
        document = await operation(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
        )
        return await self._with_skill_ids(document)

    async def create(
        self,
        *,
        user_id: str,
        payload: PersonaCreate,
        requested_workspace_id: str | None = None,
    ) -> PersonaDocument:
        """Create a persona in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        await self._require_available_skills(
            workspace_id=workspace_id,
            skill_ids=payload.skill_ids,
        )

        document = await self._instruction_service.create(
            workspace_id=workspace_id,
            instruction_type="persona",
            payload=InstructionCreate(
                name=payload.name,
                description=payload.description,
                instructions=payload.instructions,
                metadata=payload.metadata,
            ),
        )
        await self._persona_skill_repository.replace_for_persona(
            persona_id=document.id,
            skill_ids=payload.skill_ids,
        )
        return self._to_persona_document(
            document,
            skill_ids=payload.skill_ids,
        )

    async def update(
        self,
        *,
        user_id: str,
        persona_id: str,
        payload: PersonaUpdate,
        requested_workspace_id: str | None = None,
    ) -> PersonaDocument:
        """Update an existing persona."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        if payload.skill_ids is not None:
            await self._require_available_skills(
                workspace_id=workspace_id,
                skill_ids=payload.skill_ids,
            )

        document = await self._instruction_service.update(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
            payload=InstructionUpdate(
                expected_version=payload.expected_version,
                name=payload.name,
                description=payload.description,
                instructions=payload.instructions,
                metadata=payload.metadata,
            ),
        )
        if payload.skill_ids is not None:
            await self._persona_skill_repository.replace_for_persona(
                persona_id=persona_id,
                skill_ids=payload.skill_ids,
            )
        return await self._with_skill_ids(document)

    async def delete(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Delete a persona when it has no blocking dependencies."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        await self._instruction_service.delete(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
        )

    async def _require_available_skills(
        self,
        *,
        workspace_id: str,
        skill_ids: tuple[str, ...],
    ) -> None:
        """Ensure every associated skill is visible and non-deprecated."""

        for skill_id in skill_ids:
            await self._instruction_service.describe(
                workspace_id=workspace_id,
                instruction_type="skill",
                instruction_id=skill_id,
            )

    async def _with_skill_ids(
        self,
        document: DocumentType,
    ) -> PersonaResultDocument:
        """Attach persisted skill associations to a persona document."""

        skill_ids = await self._persona_skill_repository.list_for_persona(
            persona_id=document.id,
        )
        return self._to_persona_document(
            document,
            skill_ids=skill_ids,
        )

    @staticmethod
    def _to_persona_document(
        document: PersonaBaseDocument,
        *,
        skill_ids: tuple[str, ...],
    ) -> PersonaResultDocument:
        """Convert a generic instruction into its persona representation."""

        values = {
            field.name: getattr(document, field.name)
            for field in fields(document)
        }

        if isinstance(document, AvailableInstructionDocument):
            return AvailablePersonaDocument(
                **values,
                skill_ids=skill_ids,
            )

        return PersonaDocument(
            **values,
            skill_ids=skill_ids,
        )

    async def _resolve_workspace_id(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> str:
        """Resolve the workspace selected for a persona operation."""

        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return tenant.workspace_id
