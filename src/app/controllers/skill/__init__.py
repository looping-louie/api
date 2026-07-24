"""Controller for skill resource operations."""

from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.schemas.skill import (
    SkillCreateRequest,
    SkillListResponse,
    SkillPatchRequest,
    SkillResponse,
    SkillSummaryResponse,
)
from src.app.services.shared.instruction_service import (
    InstructionCreate,
    InstructionUpdate,
)
from src.app.services.skill_service import SkillService


class SkillController:
    """Coordinates skill requests and delegates business logic."""

    def __init__(self, *, skill_service: SkillService) -> None:
        """Initialize the controller with skill business operations."""

        self._skill_service = skill_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> SkillListResponse:
        """List skill summaries available in a workspace."""

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
        """Return one complete skill visible in a workspace."""

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
        """Create a new skill directly or by copying an available source."""

        if payload.source_skill_id is not None:
            document = await self._skill_service.create_from_source(
                user_id=user_id,
                source_skill_id=payload.source_skill_id,
                name=payload.name,
                requested_workspace_id=requested_workspace_id,
            )
        else:
            # Schema validation guarantees these direct-creation fields.
            assert payload.name is not None
            assert payload.instructions is not None
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

    async def patch(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillPatchRequest,
        requested_workspace_id: str | None = None,
    ) -> SkillResponse:
        """Apply supplied content and enabled-state changes."""

        if payload.has_content_changes():
            metadata = None
            if payload.metadata is not None:
                metadata = payload.metadata.model_dump(
                    exclude_none=True,
                )

            # Schema validation requires a version for content changes.
            assert payload.expected_version is not None
            await self._skill_service.update(
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

        if payload.enabled is not None:
            await self._skill_service.set_enabled(
                user_id=user_id,
                skill_id=skill_id,
                enabled=payload.enabled,
                requested_workspace_id=requested_workspace_id,
            )

        document = await self._skill_service.describe(
            user_id=user_id,
            skill_id=skill_id,
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
        """Delete an owned custom skill without blocking dependencies."""

        await self._skill_service.delete(
            user_id=user_id,
            skill_id=skill_id,
            requested_workspace_id=requested_workspace_id,
        )

        return DeleteResponse()
