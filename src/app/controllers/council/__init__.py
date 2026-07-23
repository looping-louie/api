from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.schemas.council import (
    CouncilCreateRequest,
    CouncilListResponse,
    CouncilResponse,
    CouncilSummaryResponse,
    CouncilUpdateRequest,
)
from src.app.services.council_service import (
    CouncilAssignment,
    CouncilCreate,
    CouncilService,
    CouncilUpdate,
)


class CouncilController:
    """Coordinates council requests and delegates business logic."""

    def __init__(self, *, council_service: CouncilService) -> None:
        self._council_service = council_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> CouncilListResponse:
        summaries = await self._council_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            search=search,
        )

        items = [
            CouncilSummaryResponse.model_validate(summary)
            for summary in summaries
        ]

        return CouncilListResponse(
            items=items,
            total=len(items),
        )

    async def describe(
        self,
        *,
        user_id: str,
        council_id: str,
        requested_workspace_id: str | None = None,
    ) -> CouncilResponse:
        document = await self._council_service.describe(
            user_id=user_id,
            council_id=council_id,
            requested_workspace_id=requested_workspace_id,
        )

        return CouncilResponse.model_validate(document)

    async def create(
        self,
        *,
        user_id: str,
        payload: CouncilCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> CouncilResponse:
        document = await self._council_service.create(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            payload=CouncilCreate(
                name=payload.name,
                description=payload.description,
                assignments=tuple(
                    CouncilAssignment(
                        role=assignment.role,
                        persona_id=assignment.persona_id,
                        skill_ids=tuple(assignment.skill_ids),
                    )
                    for assignment in payload.assignments
                ),
            ),
        )

        return CouncilResponse.model_validate(document)

    async def update(
        self,
        *,
        user_id: str,
        council_id: str,
        payload: CouncilUpdateRequest,
        requested_workspace_id: str | None = None,
    ) -> CouncilResponse:
        assignments = None

        if payload.assignments is not None:
            assignments = tuple(
                CouncilAssignment(
                    role=assignment.role,
                    persona_id=assignment.persona_id,
                    skill_ids=tuple(assignment.skill_ids),
                )
                for assignment in payload.assignments
            )

        document = await self._council_service.update(
            user_id=user_id,
            council_id=council_id,
            requested_workspace_id=requested_workspace_id,
            payload=CouncilUpdate(
                expected_version=payload.expected_version,
                name=payload.name,
                description=payload.description,
                assignments=assignments,
            ),
        )

        return CouncilResponse.model_validate(document)

    async def delete(
        self,
        *,
        user_id: str,
        council_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        await self._council_service.delete(
            user_id=user_id,
            council_id=council_id,
            requested_workspace_id=requested_workspace_id,
        )

        return DeleteResponse()
