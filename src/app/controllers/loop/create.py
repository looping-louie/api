"""Controller for creating loop definitions."""

from __future__ import annotations

from src.app.schemas.loop import LoopCreateRequest, LoopResponse
from src.app.services.loop_service import LoopService
from src.app.services.loop_types import LoopCreate

from .utils import loop_agents, loop_output_contract, loop_stop_conditions


class LoopCreateController:
    """Create one loop definition."""

    def __init__(self, *, loop_service: LoopService) -> None:
        """Store the loop application service."""
        self._loop_service = loop_service

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
                stop_conditions=loop_stop_conditions(payload.stop_conditions),
                agents=loop_agents(payload.agents),
                output_contract=loop_output_contract(payload.output_contract),
            ),
        )
        return LoopResponse.model_validate(document)
