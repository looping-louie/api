"""Shared request translations for pipeline controllers."""

from src.app.schemas.pipeline import (
    PipelineHumanGateStepRequest,
    PipelineLoopStepRequest,
    PipelineStepRequest,
)
from src.app.services.pipelines.types import PipelineQuizConfigInput, PipelineStepInput


def pipeline_steps(
    values: list[PipelineStepRequest],
) -> tuple[PipelineStepInput, ...]:
    """Translate validated pipeline step schemas to application inputs."""
    return tuple(pipeline_step(value) for value in values)


def pipeline_step(value: PipelineStepRequest) -> PipelineStepInput:
    """Translate one request step without applying business rules."""
    if isinstance(value, PipelineLoopStepRequest):
        return PipelineStepInput(type=value.type, loop_id=value.loop_id)
    assert isinstance(value, PipelineHumanGateStepRequest)
    config = value.config
    return PipelineStepInput(
        type=value.type,
        gate_type=value.gate_type,
        config=(
            PipelineQuizConfigInput(
                minimum_correct_answers=config.minimum_correct_answers,
                question_count=config.question_count,
                option_count=config.option_count,
            )
            if config is not None
            else None
        ),
    )
