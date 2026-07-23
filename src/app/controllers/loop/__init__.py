from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.schemas.loop import (
    LoopCreateRequest,
    LoopListResponse,
    LoopResponse,
    LoopSummaryResponse,
    LoopUpdateRequest,
    LoopValidationResponse,
)
from src.app.services.loop_service import (
    LoopCreate,
    LoopModelBinding,
    LoopService,
    LoopUpdate,
)


class LoopController:
    """Coordinates loop requests and delegates business logic."""

    def __init__(self, *, loop_service: LoopService) -> None:
        self._loop_service = loop_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> LoopListResponse:
        summaries = await self._loop_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            search=search,
        )

        items = [
            LoopSummaryResponse.model_validate(summary)
            for summary in summaries
        ]

        return LoopListResponse(
            items=items,
            total=len(items),
        )

    async def describe(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopResponse:
        document = await self._loop_service.describe(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
        )

        return LoopResponse.model_validate(document)

    async def create(
        self,
        *,
        user_id: str,
        payload: LoopCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> LoopResponse:
        document = await self._loop_service.create(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            payload=LoopCreate(
                name=payload.name,
                description=payload.description,
                council_id=payload.council_id,
                max_iterations=payload.max_iterations,
                model_bindings=tuple(
                    LoopModelBinding(
                        role=binding.role,
                        model_id=binding.model_id,
                    )
                    for binding in payload.model_bindings
                ),
            ),
        )

        return LoopResponse.model_validate(document)

    async def update(
        self,
        *,
        user_id: str,
        loop_id: str,
        payload: LoopUpdateRequest,
        requested_workspace_id: str | None = None,
    ) -> LoopResponse:
        model_bindings = None

        if payload.model_bindings is not None:
            model_bindings = tuple(
                LoopModelBinding(
                    role=binding.role,
                    model_id=binding.model_id,
                )
                for binding in payload.model_bindings
            )

        document = await self._loop_service.update(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
            payload=LoopUpdate(
                expected_version=payload.expected_version,
                name=payload.name,
                description=payload.description,
                council_id=payload.council_id,
                max_iterations=payload.max_iterations,
                model_bindings=model_bindings,
            ),
        )

        return LoopResponse.model_validate(document)

    async def delete(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        await self._loop_service.delete(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
        )

        return DeleteResponse()

    async def validate(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopValidationResponse:
        document = await self._loop_service.validate(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
        )

        return LoopValidationResponse(
            loop=LoopResponse.model_validate(document),
        )
