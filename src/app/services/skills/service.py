"""Workspace-aware application service for skill resources."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.persona_skills import (
    CATALOG_INSTRUCTION_PAGE_SIZE,
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)

from ..persona_skills import (
    AvailableInstructionDocument,
    AvailableInstructionPage,
    InstructionDocument,
    SkillDefinitionService,
)
from ..shared.tenant import TenantService
from .metadata_validator import (
    validate_skill_metadata,
)
from .types import SkillCreate, SkillUpdate


class SkillService:
    """Application service for skill operations."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        skill_definition_service: SkillDefinitionService,
    ) -> None:
        """Initialize workspace resolution and Skill definitions."""

        self._tenant_service = tenant_service
        self._skill_definition_service = skill_definition_service

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
        """Return one filtered page of skills in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._skill_definition_service.list(
            workspace_id=workspace_id,
            search=search,
            status=status,
            categories=categories,
            sort=sort,
            offset=offset,
            limit=limit,
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

        return await self._skill_definition_service.describe(
            workspace_id=workspace_id,
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
            self._skill_definition_service.enable
            if enabled
            else self._skill_definition_service.disable
        )
        return await operation(
            workspace_id=workspace_id,
            instruction_id=skill_id,
        )

    async def create(
        self,
        *,
        user_id: str,
        payload: SkillCreate,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Create a skill in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        validate_skill_metadata(payload.metadata)

        return await self._skill_definition_service.create(
            workspace_id=workspace_id,
            payload=payload,
        )

    async def update(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillUpdate,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Update an existing skill."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        if payload.metadata is not None:
            validate_skill_metadata(payload.metadata)

        return await self._skill_definition_service.update(
            workspace_id=workspace_id,
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

        await self._skill_definition_service.delete(
            workspace_id=workspace_id,
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
