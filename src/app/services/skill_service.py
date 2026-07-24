"""Workspace-aware application service for skill resources."""

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
from .skill_metadata_validator import (
    SkillValidationError,
    validate_skill_metadata,
)


__all__ = ["SkillService", "SkillValidationError"]


class SkillService:
    """Application service for skill operations."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        instruction_service: InstructionService,
    ) -> None:
        """Initialize workspace resolution and shared instruction behavior."""

        self._tenant_service = tenant_service
        self._instruction_service = instruction_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> list[AvailableInstructionSummary]:
        """List skills available in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._instruction_service.list(
            workspace_id=workspace_id,
            instruction_type="skill",
            search=search,
        )

    async def describe(
        self,
        *,
        user_id: str,
        skill_id: str,
        requested_workspace_id: str | None = None,
        include_deprecated: bool = False,
    ) -> AvailableInstructionDocument:
        """Return a complete skill."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._instruction_service.describe(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=skill_id,
            include_deprecated=include_deprecated,
        )

    async def set_enabled(
        self,
        *,
        user_id: str,
        skill_id: str,
        enabled: bool,
        requested_workspace_id: str | None = None,
    ) -> AvailableInstructionDocument:
        """Set whether a skill is enabled in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        operation = (
            self._instruction_service.enable
            if enabled
            else self._instruction_service.disable
        )
        return await operation(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=skill_id,
        )

    async def create_from_source(
        self,
        *,
        user_id: str,
        source_skill_id: str,
        name: str | None = None,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Create an editable skill copied from an available source."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return await self._instruction_service.duplicate(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=source_skill_id,
            name=name,
        )

    async def resolve_for_selection(
        self,
        *,
        user_id: str,
        skill_id: str,
        requested_workspace_id: str | None = None,
    ) -> AvailableInstructionDocument:
        """Resolve an enabled skill for a new composition."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return await self._instruction_service.resolve_for_selection(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=skill_id,
        )

    async def create(
        self,
        *,
        user_id: str,
        payload: InstructionCreate,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Create a skill in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        validate_skill_metadata(payload.metadata)

        return await self._instruction_service.create(
            workspace_id=workspace_id,
            instruction_type="skill",
            payload=payload,
        )

    async def update(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: InstructionUpdate,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Update an existing skill."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        if payload.metadata is not None:
            validate_skill_metadata(payload.metadata)

        return await self._instruction_service.update(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=skill_id,
            payload=payload,
        )

    async def delete(
        self,
        *,
        user_id: str,
        skill_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Delete a skill when it has no blocking dependencies."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        await self._instruction_service.delete(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=skill_id,
        )

    async def _resolve_workspace_id(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> str:
        """Resolve the workspace selected for a skill operation."""

        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return tenant.workspace_id
