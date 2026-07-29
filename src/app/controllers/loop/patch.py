"""Controller for patching loop definitions."""

from __future__ import annotations

from src.app.schemas.loop import LoopPatchRequest, LoopResponse
from src.app.services.loops.service import LoopService
from src.app.services.loops.types import LoopPatch

from .utils import loop_agents, loop_output_contract, loop_stop_conditions


class LoopPatchController:
    """Apply supplied fields to one loop definition."""

    def __init__(self, *, loop_service: LoopService) -> None:
        """Store the loop application service."""
        self._loop_service = loop_service

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
                    loop_stop_conditions(payload.stop_conditions)
                    if payload.stop_conditions is not None
                    else None
                ),
                agents=(
                    loop_agents(payload.agents)
                    if payload.agents is not None
                    else None
                ),
                output_contract=(
                    loop_output_contract(payload.output_contract)
                    if payload.output_contract is not None
                    else None
                ),
            ),
        )
        return LoopResponse.model_validate(document)
