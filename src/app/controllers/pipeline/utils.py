"""Shared request translations for pipeline controllers."""

from src.app.schemas.pipeline import (
    PipelineActivityStepRequest,
)
from src.app.services.pipelines.types import PipelineActivityInput


def pipeline_steps(
    values: list[PipelineActivityStepRequest],
) -> tuple[PipelineActivityInput, ...]:
    """Translate validated pipeline step schemas to application inputs."""
    return tuple(pipeline_step(value) for value in values)


def pipeline_step(value: PipelineActivityStepRequest) -> PipelineActivityInput:
    """Translate one request step without applying business rules."""
    return PipelineActivityInput(
        title=value.title,
        description=value.description,
        type=value.type,
        config=value.config.model_dump(by_alias=True),
    )
