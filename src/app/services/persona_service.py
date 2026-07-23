from __future__ import annotations

from .shared.instruction_service import (
    AvailableInstructionDocument,
    AvailableInstructionSummary,
    InstructionCreate,
    InstructionDocument,
    InstructionService,
    InstructionUpdate,
)
from .shared.tenant_service import TenantService


class PersonaService:
    """Application service for persona operations."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        instruction_service: InstructionService,
    ) -> None:
        self._tenant_service = tenant_service
        self._instruction_service = instruction_service

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
    ) -> AvailableInstructionDocument:
        """Return a complete persona."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._instruction_service.describe(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
            include_deprecated=include_deprecated,
        )

    async def enable(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
    ) -> AvailableInstructionDocument:
        """Enable a persona in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return await self._instruction_service.enable(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
        )

    async def disable(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
    ) -> AvailableInstructionDocument:
        """Disable a persona in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return await self._instruction_service.disable(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
        )

    async def duplicate(
        self,
        *,
        user_id: str,
        persona_id: str,
        name: str | None = None,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Fork a persona into an editable workspace custom."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return await self._instruction_service.duplicate(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
            name=name,
        )

    async def resolve_for_selection(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
    ) -> AvailableInstructionDocument:
        """Resolve an enabled persona for a new composition."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return await self._instruction_service.resolve_for_selection(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
        )

    async def create(
        self,
        *,
        user_id: str,
        payload: InstructionCreate,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Create a persona in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        self._validate_create(payload)

        return await self._instruction_service.create(
            workspace_id=workspace_id,
            instruction_type="persona",
            payload=payload,
        )

    async def update(
        self,
        *,
        user_id: str,
        persona_id: str,
        payload: InstructionUpdate,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Update an existing persona."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        self._validate_update(payload)

        return await self._instruction_service.update(
            workspace_id=workspace_id,
            instruction_type="persona",
            instruction_id=persona_id,
            payload=payload,
        )

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

    async def _resolve_workspace_id(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> str:
        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return tenant.workspace_id

    @staticmethod
    def _validate_create(payload: InstructionCreate) -> None:
        """
        Validate persona-specific creation rules.

        No additional persona rules are currently required. Generic name,
        content, metadata and uniqueness checks belong to InstructionService.
        """

        del payload

    @staticmethod
    def _validate_update(payload: InstructionUpdate) -> None:
        """
        Validate persona-specific update rules.

        This method intentionally remains explicit so future persona-only
        constraints do not leak into InstructionService.
        """

        del payload
