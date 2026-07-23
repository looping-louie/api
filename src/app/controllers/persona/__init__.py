from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.schemas.persona import (
    PersonaCreateRequest,
    PersonaDuplicateRequest,
    PersonaEnabledRequest,
    PersonaListResponse,
    PersonaResponse,
    PersonaSummaryResponse,
    PersonaUpdateRequest,
)
from src.app.services.persona_service import PersonaService
from src.app.services.shared.instruction_service import (
    InstructionCreate,
    InstructionUpdate,
)


class PersonaController:
    """Coordinates persona requests and delegates business logic."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        self._persona_service = persona_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> PersonaListResponse:
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
        document = await self._persona_service.create(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            payload=InstructionCreate(
                name=payload.name,
                description=payload.description,
                instructions=payload.instructions,
                metadata=payload.metadata,
            ),
        )
        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )

        return PersonaResponse.model_validate(document)

    async def update(
        self,
        *,
        user_id: str,
        persona_id: str,
        payload: PersonaUpdateRequest,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        document = await self._persona_service.update(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
            payload=InstructionUpdate(
                expected_version=payload.expected_version,
                name=payload.name,
                description=payload.description,
                instructions=payload.instructions,
                metadata=payload.metadata,
            ),
        )
        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )

        return PersonaResponse.model_validate(document)

    async def set_enabled(
        self,
        *,
        user_id: str,
        persona_id: str,
        payload: PersonaEnabledRequest,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        """Set the effective enablement of a persona for one workspace."""

        operation = (
            self._persona_service.enable
            if payload.enabled
            else self._persona_service.disable
        )
        document = await operation(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
        )

        return PersonaResponse.model_validate(document)

    async def duplicate(
        self,
        *,
        user_id: str,
        persona_id: str,
        payload: PersonaDuplicateRequest,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        """Fork an available persona into an editable custom copy."""

        duplicate = await self._persona_service.duplicate(
            user_id=user_id,
            persona_id=persona_id,
            name=payload.name,
            requested_workspace_id=requested_workspace_id,
        )
        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=duplicate.id,
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
        await self._persona_service.delete(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
        )

        return DeleteResponse()
