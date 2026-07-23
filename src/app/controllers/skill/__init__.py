from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.schemas.skill import (
    SkillCreateRequest,
    SkillDuplicateRequest,
    SkillEnabledRequest,
    SkillListResponse,
    SkillResponse,
    SkillSummaryResponse,
    SkillUpdateRequest,
)
from src.app.services.shared.instruction_service import (
    InstructionCreate,
    InstructionUpdate,
)
from src.app.services.skill_service import SkillService


class SkillController:
    """Coordinates skill requests and delegates business logic."""

    def __init__(self, *, skill_service: SkillService) -> None:
        self._skill_service = skill_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> SkillListResponse:
        summaries = await self._skill_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            search=search,
        )

        items = [
            SkillSummaryResponse.model_validate(summary)
            for summary in summaries
        ]

        return SkillListResponse(
            items=items,
            total=len(items),
        )

    async def describe(
        self,
        *,
        user_id: str,
        skill_id: str,
        requested_workspace_id: str | None = None,
    ) -> SkillResponse:
        document = await self._skill_service.describe(
            user_id=user_id,
            skill_id=skill_id,
            requested_workspace_id=requested_workspace_id,
        )

        return SkillResponse.model_validate(document)

    async def create(
        self,
        *,
        user_id: str,
        payload: SkillCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> SkillResponse:
        document = await self._skill_service.create(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            payload=InstructionCreate(
                name=payload.name,
                description=payload.description,
                instructions=payload.instructions,
                metadata=payload.metadata.model_dump(
                    exclude_none=True,
                ),
            ),
        )
        document = await self._skill_service.describe(
            user_id=user_id,
            skill_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )

        return SkillResponse.model_validate(document)

    async def update(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillUpdateRequest,
        requested_workspace_id: str | None = None,
    ) -> SkillResponse:
        metadata = None

        if payload.metadata is not None:
            metadata = payload.metadata.model_dump(
                exclude_none=True,
            )

        document = await self._skill_service.update(
            user_id=user_id,
            skill_id=skill_id,
            requested_workspace_id=requested_workspace_id,
            payload=InstructionUpdate(
                expected_version=payload.expected_version,
                name=payload.name,
                description=payload.description,
                instructions=payload.instructions,
                metadata=metadata,
            ),
        )
        document = await self._skill_service.describe(
            user_id=user_id,
            skill_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )

        return SkillResponse.model_validate(document)

    async def set_enabled(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillEnabledRequest,
        requested_workspace_id: str | None = None,
    ) -> SkillResponse:
        """Set the effective enablement of a skill for one workspace."""

        operation = (
            self._skill_service.enable
            if payload.enabled
            else self._skill_service.disable
        )
        document = await operation(
            user_id=user_id,
            skill_id=skill_id,
            requested_workspace_id=requested_workspace_id,
        )

        return SkillResponse.model_validate(document)

    async def duplicate(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillDuplicateRequest,
        requested_workspace_id: str | None = None,
    ) -> SkillResponse:
        """Fork an available skill into an editable custom copy."""

        duplicate = await self._skill_service.duplicate(
            user_id=user_id,
            skill_id=skill_id,
            name=payload.name,
            requested_workspace_id=requested_workspace_id,
        )
        document = await self._skill_service.describe(
            user_id=user_id,
            skill_id=duplicate.id,
            requested_workspace_id=requested_workspace_id,
        )

        return SkillResponse.model_validate(document)

    async def delete(
        self,
        *,
        user_id: str,
        skill_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        await self._skill_service.delete(
            user_id=user_id,
            skill_id=skill_id,
            requested_workspace_id=requested_workspace_id,
        )

        return DeleteResponse()
