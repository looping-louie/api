"""Workspace-aware application service for skill resources."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.skills import SkillCategory, SkillSort, SkillStatus

from ..instructions import (
    AvailableInstructionDocument,
    AvailableInstructionSummary,
    InstructionCreate,
    InstructionDocument,
    InstructionService,
    InstructionUpdate,
)
from ..shared.tenant import TenantService
from .metadata_validator import (
    validate_skill_metadata,
)


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
        status: SkillStatus | None = None,
        categories: Sequence[SkillCategory] = (),
        sort: SkillSort | None = None,
    ) -> list[AvailableInstructionSummary]:
        """List skills available in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        summaries = await self._instruction_service.list(
            workspace_id=workspace_id,
            instruction_type="skill",
            search=search,
        )

        if status is not None:
            enabled = status == SkillStatus.ENABLED
            summaries = [
                summary
                for summary in summaries
                if summary.enabled is enabled
            ]

        if categories:
            selected_categories = {
                category.value
                for category in categories
            }
            summaries = [
                summary
                for summary in summaries
                if summary.category in selected_categories
            ]

        return self._sort_summaries(summaries, sort=sort)

    @staticmethod
    def _sort_summaries(
        summaries: list[AvailableInstructionSummary],
        *,
        sort: SkillSort | None,
    ) -> list[AvailableInstructionSummary]:
        """Return a stable ordering for one filtered skill collection."""

        if sort == SkillSort.ALPHABETICAL_DESC:
            return sorted(
                summaries,
                key=lambda summary: (
                    summary.name.casefold(),
                    summary.id,
                ),
                reverse=True,
            )

        if sort == SkillSort.NEWEST:
            return sorted(
                summaries,
                key=lambda summary: (
                    -summary.created_at.timestamp(),
                    summary.name.casefold(),
                    summary.id,
                ),
            )

        if sort == SkillSort.OLDEST:
            return sorted(
                summaries,
                key=lambda summary: (
                    summary.created_at,
                    summary.name.casefold(),
                    summary.id,
                ),
            )

        return sorted(
            summaries,
            key=lambda summary: (
                summary.name.casefold(),
                summary.id,
            ),
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
