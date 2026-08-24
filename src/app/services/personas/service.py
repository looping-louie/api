"""Workspace-aware application service for persona resources."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields

from src.app.catalogs.persona_skills import (
    CATALOG_INSTRUCTION_PAGE_SIZE,
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)

from ..persona_skills import (
    AvailableInstructionDocument,
    AvailableInstructionPage,
    DefinitionCreate,
    DefinitionUpdate,
    PersonaDefinitionService,
    SkillDefinitionService,
)
from ..shared.tenant import TenantService
from ..shared.reference_resolver import (
    ReferenceResolver,
    ResourceReference,
)
from ..linked_services import LinkedServiceService
from .types import (
    AvailablePersonaDocument,
    AvailablePersonaSummary,
    DocumentType,
    PersonaBaseDocument,
    PersonaCreate,
    PersonaDocument,
    PersonaLinkedServiceSelection,
    PersonaLinkedServiceSelectionRepository,
    PersonaResultDocument,
    PersonaSkillRepository,
    PersonaUpdate,
)


class PersonaService:
    """Application service for persona operations."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        persona_definition_service: PersonaDefinitionService,
        skill_definition_service: SkillDefinitionService,
        persona_skill_repository: PersonaSkillRepository,
        reference_resolver: ReferenceResolver,
        persona_linked_service_selection_repository: PersonaLinkedServiceSelectionRepository,
        linked_service_service: LinkedServiceService,
    ) -> None:
        """Initialize workspace resolution and Persona/Skill definitions."""

        self._tenant_service = tenant_service
        self._persona_definition_service = persona_definition_service
        self._skill_definition_service = skill_definition_service
        self._persona_skill_repository = persona_skill_repository
        self._persona_linked_service_selection_repository = persona_linked_service_selection_repository
        self._linked_service_service = linked_service_service
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

        page = await self._persona_definition_service.list(
            workspace_id=workspace_id,
            search=search,
            status=status,
            categories=categories,
            sort=sort,
            offset=offset,
            limit=limit,
        )
        items: list[AvailablePersonaSummary] = []
        for summary in page.items:
            linked_service_selection = (
                await self._persona_linked_service_selection_repository.get_for_persona(
                    workspace_id=workspace_id,
                    persona_id=summary.id,
                )
            )
            items.append(
                AvailablePersonaSummary(
                    **{
                        field.name: getattr(summary, field.name)
                        for field in fields(summary)
                    },
                    linked_service_selection=linked_service_selection,
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

        document = await self._persona_definition_service.describe(
            workspace_id=workspace_id,
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
            self._persona_definition_service.enable
            if enabled
            else self._persona_definition_service.disable
        )
        document = await operation(
            workspace_id=workspace_id,
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
        if payload.linked_service_selection is None:
            raise ValueError(
                'Persona linked-service selection is required.'
            )
        await self._require_available_skills(
            workspace_id=workspace_id,
            skill_ids=payload.skill_ids,
        )
        await self._require_linked_service_selection(
            workspace_id=workspace_id,
            selection=payload.linked_service_selection,
        )

        document = await self._persona_definition_service.create(
            workspace_id=workspace_id,
            payload=DefinitionCreate(
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
        await self._persona_linked_service_selection_repository.replace_for_persona(
            workspace_id=workspace_id,
            persona_id=document.id,
            selection=payload.linked_service_selection,
        )
        return self._to_persona_document(
            document,
            linked_service_selection=payload.linked_service_selection,
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
        if payload.linked_service_selection_supplied:
            if payload.linked_service_selection is None:
                raise ValueError(
                    'Persona linked-service selection cannot be removed.'
                )
            await self._require_linked_service_selection(
                workspace_id=workspace_id,
                selection=payload.linked_service_selection,
            )

        if any(
            value is not None
            for value in (
                payload.name,
                payload.description,
                payload.instructions,
                payload.metadata,
            )
        ):
            document = await self._persona_definition_service.update(
                workspace_id=workspace_id,
                instruction_id=persona_id,
                payload=DefinitionUpdate(
                    expected_version=payload.expected_version,
                    name=payload.name,
                    description=payload.description,
                    instructions=payload.instructions,
                    metadata=payload.metadata,
                ),
            )
        else:
            document = await self._persona_definition_service.describe(
                workspace_id=workspace_id,
                instruction_id=persona_id,
            )
        if payload.skill_ids is not None:
            await self._persona_skill_repository.replace_for_persona(
                persona_id=persona_id,
                skill_ids=payload.skill_ids,
            )
        if payload.linked_service_selection_supplied:
            await self._persona_linked_service_selection_repository.replace_for_persona(
                workspace_id=workspace_id,
                persona_id=persona_id,
                selection=payload.linked_service_selection,
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

        await self._persona_definition_service.delete(
            workspace_id=workspace_id,
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
            await self._skill_definition_service.describe(
                workspace_id=workspace_id,
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
        linked_service_selection = (
            await self._persona_linked_service_selection_repository.get_for_persona(
                workspace_id=document.workspace_id,
                persona_id=document.id,
            )
        )
        return self._to_persona_document(
            document,
            linked_service_selection=linked_service_selection,
            skill_ids=skill_ids,
        )

    @staticmethod
    def _to_persona_document(
        document: PersonaBaseDocument,
        *,
        linked_service_selection: PersonaLinkedServiceSelection | None,
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
                linked_service_selection=linked_service_selection,
                skill_ids=skill_ids,
            )

        return PersonaDocument(
            **values,
            linked_service_selection=linked_service_selection,
            skill_ids=skill_ids,
        )

    async def _require_linked_service_selection(
        self,
        *,
        workspace_id: str,
        selection: PersonaLinkedServiceSelection,
    ) -> None:
        """Ensure the selected linked service can deploy the requested model."""

        await self._linked_service_service.require_available_selection(
            workspace_id=workspace_id,
            service_id=selection.linked_service_id,
            model_id=selection.model_id,
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
