"""Shared request translations for pipeline controllers."""

from src.app.schemas.pipeline import (
    PipelineActivityStepRequest,
    PipelineResponse,
)
from src.app.schemas.activity import ActivityResponse
from src.app.models.pipeline import PipelineDetails
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


def pipeline_details_response(details: PipelineDetails) -> PipelineResponse:
    """Translate ordered pipeline Activity documents to the detailed response."""

    document = details.document
    return PipelineResponse(
        id=document.id,
        title=document.title,
        description=document.description,
        enabled=document.enabled,
        steps=[
            ActivityResponse.model_validate(activity)
            for activity in details.activities
        ],
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
