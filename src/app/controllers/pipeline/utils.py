"""Shared request translations for pipeline controllers."""

from src.app.schemas.pipeline import (
    PipelineActivityStepRequest,
    PipelineActivityStepResponse,
    PipelineHarnessRequest,
    PipelineHarnessResponse,
    PipelineStepDependencyResponse,
    PipelineResponse,
)
from src.app.models.pipeline import PipelineDetails
from src.app.services.pipelines.types import PipelineActivityInput, PipelineHarnessInput
from src.app.services.pipelines.types import PipelineActivityDependencyInput


def pipeline_steps(
    values: list[PipelineActivityStepRequest],
) -> tuple[PipelineActivityInput, ...]:
    """Translate validated pipeline step schemas to application inputs."""
    return tuple(pipeline_step(value) for value in values)


def pipeline_step(value: PipelineActivityStepRequest) -> PipelineActivityInput:
    """Translate one request step without applying business rules."""
    return PipelineActivityInput(
        name=value.name,
        description=value.description,
        type=value.type,
        config=value.config.model_dump(by_alias=True),
        model_id=value.model_id,
        harness=pipeline_harness(value.harness),
        depends_on=tuple(
            PipelineActivityDependencyInput(
                activity=dependency.activity,
                condition=dependency.condition,
            )
            for dependency in value.depends_on
        ),
    )


def pipeline_harness(
    value: PipelineHarnessRequest | None,
) -> PipelineHarnessInput | None:
    """Translate one Pipeline Harness request without business validation."""

    if value is None:
        return None
    return PipelineHarnessInput(
        kind=value.kind,
        version=value.version,
        config=dict(value.config),
    )


def pipeline_details_response(details: PipelineDetails) -> PipelineResponse:
    """Translate ordered pipeline Activity documents to the detailed response."""

    document = details.document
    return PipelineResponse(
        id=document.id,
        name=document.name,
        description=document.description,
        enabled=document.enabled,
        model_id=document.model_id,
        harness=(
            PipelineHarnessResponse(
                kind=document.harness.kind,
                version=document.harness.version,
                config=dict(document.harness.config),
            )
            if document.harness is not None
            else None
        ),
        steps=_step_responses(details),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _step_responses(
    details: PipelineDetails,
) -> list[PipelineActivityStepResponse]:
    """Attach named graph dependencies to resolved Activity responses."""

    activity_names = {
        activity.id: activity.name
        for activity in details.activities
    }
    return [
        PipelineActivityStepResponse.model_validate(activity).model_copy(
            update={
                'depends_on': [
                PipelineStepDependencyResponse(
                    activity=activity_names[dependency.activity_id],
                    condition=dependency.condition,
                )
                for dependency in step.depends_on
                ],
            },
        )
        for step, activity in zip(
            details.document.steps,
            details.activities,
            strict=True,
        )
    ]
