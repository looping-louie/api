"""Shared request translations for loop controllers."""

from src.app.models.loop import LoopOutputContract, LoopStopConditions
from src.app.schemas.loop import (
    LoopAgentSchema,
    LoopOutputContractSchema,
    LoopStopConditionsSchema,
)
from src.app.services.loops.types import LoopAgentInput


def loop_agents(values: list[LoopAgentSchema]) -> tuple[LoopAgentInput, ...]:
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


def loop_stop_conditions(value: LoopStopConditionsSchema) -> LoopStopConditions:
    """Translate a stop-condition request schema."""
    return LoopStopConditions(
        max_iterations=value.max_iterations,
        max_tokens=value.max_tokens,
        timeout_seconds=value.timeout_seconds,
    )


def loop_output_contract(value: LoopOutputContractSchema) -> LoopOutputContract:
    """Translate an output-contract request schema."""
    return LoopOutputContract(
        type=value.type,
        description=value.description,
        files=tuple(value.files),
        schema=value.schema_,
    )
