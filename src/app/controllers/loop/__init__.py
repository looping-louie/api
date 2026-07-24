"""Controller for loop HTTP operations."""

from __future__ import annotations

from src.app.models.loop import LoopOutputContract, LoopStopConditions
from src.app.schemas.common import DeleteResponse
from src.app.schemas.loop import (
    LoopAgentSchema,
    LoopChangelogEntryResponse,
    LoopChangelogListResponse,
    LoopCreateRequest,
    LoopListResponse,
    LoopOutputContractSchema,
    LoopPatchRequest,
    LoopResponse,
    LoopStopConditionsSchema,
)
from src.app.services.loop_service import LoopService
from src.app.services.loop_types import (
    LoopAgentInput,
    LoopCreate,
    LoopPatch,
)


class LoopController:
    """Translate loop HTTP schemas to and from application values."""

    def __init__(self, *, loop_service: LoopService) -> None:
        """Store the loop application service."""

        self._loop_service = loop_service

    async def list(
        self,
        *,
        user_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> LoopListResponse:
        """Return one loop page."""

        documents, total = await self._loop_service.list(
            user_id=user_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return LoopListResponse(
            items=[
                LoopResponse.model_validate(document)
                for document in documents
            ],
            total=total,
        )

    async def get(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopResponse:
        """Return one loop."""

        document = await self._loop_service.get(
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
        """Create one loop."""

        document = await self._loop_service.create(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            payload=LoopCreate(
                title=payload.title,
                description=payload.description,
                flow=payload.flow,
                stop_conditions=self._stop_conditions(
                    payload.stop_conditions
                ),
                agents=self._agents(payload.agents),
                output_contract=self._output_contract(
                    payload.output_contract
                ),
            ),
        )
        return LoopResponse.model_validate(document)

    async def patch(
        self,
        *,
        user_id: str,
        loop_id: str,
        payload: LoopPatchRequest,
        requested_workspace_id: str | None = None,
    ) -> LoopResponse:
        """Apply supplied fields to one loop."""

        document = await self._loop_service.patch(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
            payload=LoopPatch(
                provided_fields=frozenset(payload.model_fields_set),
                title=payload.title,
                description=payload.description,
                flow=payload.flow,
                status=payload.status,
                stop_conditions=(
                    self._stop_conditions(payload.stop_conditions)
                    if payload.stop_conditions is not None
                    else None
                ),
                agents=(
                    self._agents(payload.agents)
                    if payload.agents is not None
                    else None
                ),
                output_contract=(
                    self._output_contract(payload.output_contract)
                    if payload.output_contract is not None
                    else None
                ),
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
        """Delete one loop definition."""

        await self._loop_service.delete(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
        )
        return DeleteResponse()

    async def list_changelog(
        self,
        *,
        user_id: str,
        loop_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> LoopChangelogListResponse:
        """Return one newest-first changelog page."""

        entries, total = await self._loop_service.list_changelog(
            user_id=user_id,
            loop_id=loop_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return LoopChangelogListResponse(
            items=[
                LoopChangelogEntryResponse.model_validate(entry)
                for entry in entries
            ],
            total=total,
        )

    @staticmethod
    def _agents(values: list[LoopAgentSchema]) -> tuple[LoopAgentInput, ...]:
        """Translate agent request schemas."""

        return tuple(
            LoopAgentInput(
                id=value.id,
                model_id=value.model_id,
                persona_id=value.persona_id,
                role=value.role,
            )
            for value in values
        )

    @staticmethod
    def _stop_conditions(
        value: LoopStopConditionsSchema,
    ) -> LoopStopConditions:
        """Translate a stop-condition request schema."""

        return LoopStopConditions(
            max_iterations=value.max_iterations,
            max_tokens=value.max_tokens,
            timeout_seconds=value.timeout_seconds,
        )

    @staticmethod
    def _output_contract(
        value: LoopOutputContractSchema,
    ) -> LoopOutputContract:
        """Translate an output-contract request schema."""

        return LoopOutputContract(
            type=value.type,
            description=value.description,
            files=tuple(value.files),
            schema=value.schema_,
        )
