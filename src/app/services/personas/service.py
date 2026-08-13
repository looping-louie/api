"""Workspace-aware application service for persona resources."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields

from src.app.catalogs.instructions import (
    CATALOG_INSTRUCTION_PAGE_SIZE,
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)

from ..instructions import (
    AvailableInstructionDocument,
    AvailableInstructionPage,
    InstructionCreate,
    InstructionService,
    InstructionUpdate,
)
from ..shared.tenant import TenantService
from ..shared.reference_resolver import (
    ReferenceResolver,
    ResourceReference,
)
from .types import (
    AvailablePersonaDocument,
    AvailablePersonaSummary,
    DocumentType,
    PersonaBaseDocument,
    PersonaCreate,
    PersonaDocument,
    PersonaModelRepository,
    PersonaResultDocument,
    PersonaSummaryDocument,
    PersonaSkillRepository,
    PersonaUpdate,
)


class PersonaService:
    """Application service for persona operations."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        instruction_service: InstructionService,
        persona_skill_repository: PersonaSkillRepository,
        persona_model_repository: PersonaModelRepository,
        reference_resolver: ReferenceResolver,
    ) -> None:
        """Initialize workspace resolution and shared instruction behavior."""

        self._tenant_service = tenant_service
        self._instruction_service = instruction_service
        self._persona_skill_repository = persona_skill_repository
        self._persona_model_repository = persona_model_repository
        self._reference_resolver = reference_resolver

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
        status: CatalogInstructionStatus | None = None,
        categories: Sequence[CatalogInstructionCategory] = (),
        sort: CatalogInstructionSort | None = None,
        offset: int = 0,
        limit: int = CATALOG_INSTRUCTION_PAGE_SIZE,
    ) -> AvailableInstructionPage:
        """Return one filtered page of personas in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        page = await self._instruction_service.list(
            workspace_id=workspace_id,
            instruction_type="persona",
            search=search,
            status=status,
            categories=categories,
            sort=sort,
            offset=offset,
            limit=limit,
        )
        items: list[AvailablePersonaSummary] = []
        for summary in page.items:
            model = await self._persona_model_repository.get_for_persona(
                persona_id=summary.id,
            )
            items.append(
                AvailablePersonaSummary(
                    **{
                        field.name: getattr(summary, field.name)
                        for field in fields(summary)
                    },
                    model=model,
                )
            )
        return AvailableInstructionPage(items=tuple(items), total=page.total)

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
        await self._require_model(
            workspace_id=workspace_id,
            model_id=payload.model,
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
        await self._persona_model_repository.replace_for_persona(
            persona_id=document.id,
            model_id=payload.model,
        )
        return self._to_persona_document(
            document,
            model=payload.model,
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
        await self._require_model(
            workspace_id=workspace_id,
            model_id=payload.model,
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
        if payload.model is not None:
            await self._persona_model_repository.replace_for_persona(
                persona_id=persona_id,
                model_id=payload.model,
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
        model = await self._persona_model_repository.get_for_persona(
            persona_id=document.id,
        )
        return self._to_persona_document(
            document,
            model=model,
            skill_ids=skill_ids,
        )

    @staticmethod
    def _to_persona_document(
        document: PersonaBaseDocument,
        *,
        model: str | None,
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
                model=model,
                skill_ids=skill_ids,
            )

        return PersonaDocument(
            **values,
            model=model,
            skill_ids=skill_ids,
        )

    async def _require_model(
        self,
        *,
        workspace_id: str,
        model_id: str | None,
    ) -> None:
        """Require a supplied Persona model to resolve in the workspace."""

        if model_id is None:
            return
        await self._reference_resolver.require_many(
            workspace_id=workspace_id,
            references=[ResourceReference("model", model_id)],
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
