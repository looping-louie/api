"""Controller for persona resource operations."""

from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.schemas.persona import (
    PersonaCreateRequest,
    PersonaListResponse,
    PersonaPatchRequest,
    PersonaResponse,
    PersonaSummaryResponse,
)
from src.app.services.persona_service import (
    PersonaCreate,
    PersonaService,
    PersonaUpdate,
)


class PersonaController:
    """Coordinates persona requests and delegates business logic."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        """Initialize the controller with persona business operations."""

        self._persona_service = persona_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> PersonaListResponse:
        """List persona summaries available in a workspace."""

        summaries = await self._persona_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            search=search,
        )

        items = [
            PersonaSummaryResponse.model_validate(summary)
            for summary in summaries
        ]

        return PersonaListResponse(
            items=items,
            total=len(items),
        )

    async def describe(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        """Return one complete persona visible in a workspace."""

        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
        )

        return PersonaResponse.model_validate(document)

    async def create(
        self,
        *,
        user_id: str,
        payload: PersonaCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        """Create a new persona directly or by copying an available source."""

        if payload.source_persona_id is not None:
            document = await self._persona_service.create_from_source(
                user_id=user_id,
                source_persona_id=payload.source_persona_id,
                name=payload.name,
                requested_workspace_id=requested_workspace_id,
            )
        else:
            # Schema validation guarantees these direct-creation fields.
            assert payload.name is not None
            assert payload.instructions is not None
            document = await self._persona_service.create(
                user_id=user_id,
                requested_workspace_id=requested_workspace_id,
                payload=PersonaCreate(
                    name=payload.name,
                    description=payload.description,
                    instructions=payload.instructions,
                    metadata=payload.metadata,
                    skill_ids=tuple(payload.skill_ids),
                ),
            )
        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )

        return PersonaResponse.model_validate(document)

    async def patch(
        self,
        *,
        user_id: str,
        persona_id: str,
        payload: PersonaPatchRequest,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        """Apply supplied content and enabled-state changes."""

        if payload.has_content_changes():
            # Schema validation requires a version for content changes.
            assert payload.expected_version is not None
            await self._persona_service.update(
                user_id=user_id,
                persona_id=persona_id,
                requested_workspace_id=requested_workspace_id,
                payload=PersonaUpdate(
                    expected_version=payload.expected_version,
                    name=payload.name,
                    description=payload.description,
                    instructions=payload.instructions,
                    metadata=payload.metadata,
                    skill_ids=(
                        tuple(payload.skill_ids)
                        if payload.skill_ids is not None
                        else None
                    ),
                ),
            )

        if payload.enabled is not None:
            await self._persona_service.set_enabled(
                user_id=user_id,
                persona_id=persona_id,
                enabled=payload.enabled,
                requested_workspace_id=requested_workspace_id,
            )

        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
        )

        return PersonaResponse.model_validate(document)

    async def delete(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        """Delete an owned custom persona without blocking dependencies."""

        await self._persona_service.delete(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
        )

        return DeleteResponse()
