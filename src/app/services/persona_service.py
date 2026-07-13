from __future__ import annotations

from .shared.instruction_service import (
    InstructionCreate,
    InstructionDocument,
    InstructionService,
    InstructionSummary,
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
    ) -> list[InstructionSummary]:
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
    ) -> InstructionDocument:
        """Return a complete persona."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._instruction_service.describe(
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
