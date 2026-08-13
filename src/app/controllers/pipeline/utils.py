"""Shared request translations for pipeline controllers."""

from src.app.schemas.pipeline import (
    PipelineActivityStepRequest,
)
from src.app.services.pipelines.types import PipelineStepInput


def pipeline_steps(
    values: list[PipelineActivityStepRequest],
) -> tuple[PipelineStepInput, ...]:
    """Translate validated pipeline step schemas to application inputs."""
    return tuple(pipeline_step(value) for value in values)


def pipeline_step(value: PipelineActivityStepRequest) -> PipelineStepInput:
    """Translate one request step without applying business rules."""
    return PipelineStepInput(activity_id=value.activity_id)
