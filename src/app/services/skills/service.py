"""User-owned application service for skill resources."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.persona_skills import (
    CATALOG_INSTRUCTION_PAGE_SIZE,
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)

from ..persona_skills import (
    AvailableDefinitionDocument,
    AvailableDefinitionPage,
    DefinitionDocument,
    SkillDefinitionService,
)
from ..users import UserService
from .metadata_validator import (
    validate_skill_metadata,
)
from .types import SkillCreate, SkillUpdate


class SkillService:
    """Application service for skill operations."""

    def __init__(
        self,
        *,
        user_service: UserService,
        skill_definition_service: SkillDefinitionService,
    ) -> None:
        """Initialize registered-user Skill definitions."""

        self._user_service = user_service
        self._skill_definition_service = skill_definition_service

    async def list(
        self,
        *,
        user_id: str,
        search: str | None = None,
        status: CatalogInstructionStatus | None = None,
        categories: Sequence[CatalogInstructionCategory] = (),
        sort: CatalogInstructionSort | None = None,
        offset: int = 0,
        limit: int = CATALOG_INSTRUCTION_PAGE_SIZE,
    ) -> AvailableDefinitionPage:
        """Return one filtered page of skills owned by a registered user."""

        await self._user_service.get(user_id=user_id)

        return await self._skill_definition_service.list(
            project_id=user_id,
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
        include_deprecated: bool = False,
    ) -> AvailableDefinitionDocument:
        """Return a complete skill."""

        await self._user_service.get(user_id=user_id)

        return await self._skill_definition_service.describe(
            project_id=user_id,
            instruction_id=skill_id,
            include_deprecated=include_deprecated,
        )

    async def set_enabled(
        self,
        *,
        user_id: str,
        skill_id: str,
        enabled: bool,
    ) -> AvailableDefinitionDocument:
        """Set whether a skill is enabled for a registered user."""

        await self._user_service.get(user_id=user_id)
        operation = (
            self._skill_definition_service.enable
            if enabled
            else self._skill_definition_service.disable
        )
        return await operation(
            project_id=user_id,
            instruction_id=skill_id,
        )

    async def create(
        self,
        *,
        user_id: str,
        payload: SkillCreate,
    ) -> DefinitionDocument:
        """Create a skill owned by a registered user."""

        await self._user_service.get(user_id=user_id)

        validate_skill_metadata(payload.metadata)

        return await self._skill_definition_service.create(
            project_id=user_id,
            payload=payload,
        )

    async def update(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillUpdate,
    ) -> DefinitionDocument:
        """Update an existing skill."""

        await self._user_service.get(user_id=user_id)

        if payload.metadata is not None:
            validate_skill_metadata(payload.metadata)

        return await self._skill_definition_service.update(
            project_id=user_id,
            instruction_id=skill_id,
            payload=payload,
        )

    async def delete(
        self,
        *,
        user_id: str,
        skill_id: str,
    ) -> None:
        """Delete a skill when it has no blocking dependencies."""

        await self._user_service.get(user_id=user_id)

        await self._skill_definition_service.delete(
            project_id=user_id,
            instruction_id=skill_id,
        )
