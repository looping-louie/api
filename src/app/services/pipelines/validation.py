"""Normalization and validation rules for complete pipelines."""

from __future__ import annotations

from src.app.models.changelog import JsonObject
from src.app.models.pipeline import (
    PipelineActivityStep,
    PipelineDocument,
    PipelineStatus,
    PipelineStep,
)
from src.app.services.pipelines.types import (
    InvalidPipelineStepsError,
    PipelineStepInput,
)


def require_text(value: object, field_name: str) -> str:
    """Return stripped non-empty text."""

    if not isinstance(value, str) or not value.strip():
        raise InvalidPipelineStepsError(
            field_name=field_name,
            message="must be a non-empty string",
        )
    return value.strip()


def normalize_description(value: object) -> str:
    """Return a description after validating its string type."""

    if not isinstance(value, str):
        raise InvalidPipelineStepsError(
            field_name="description",
            message="must be a string",
        )
    return value.strip()


def normalize_status(value: object) -> PipelineStatus:
    """Return one supported persisted pipeline status."""

    if value not in {"active", "disabled", "archived"}:
        raise InvalidPipelineStepsError(
            field_name="status",
            message="must be active, disabled, or archived",
        )
    return value  # type: ignore[return-value]


def normalize_steps(
    values: object,
) -> tuple[PipelineStep, ...]:
    """Validate a complete ordered step collection."""

    if not isinstance(values, (tuple, list)):
        raise InvalidPipelineStepsError(
            field_name="steps",
            message="must be an array",
        )
    if len(values) < 2:
        raise InvalidPipelineStepsError(
            field_name="steps",
            message="must contain at least two steps",
        )

    steps: list[PipelineStep] = []
    for position, value in enumerate(values):
        if not isinstance(value, PipelineStepInput):
            raise InvalidPipelineStepsError(
                field_name=f"steps.{position}",
                message="must be a pipeline step",
            )
        steps.append(
            PipelineActivityStep(
                activity_id=require_text(
                    value.activity_id,
                    f"steps.{position}.activity_id",
                )
            )
        )
    return tuple(steps)


def step_content(step: PipelineStep) -> JsonObject:
    """Serialize one domain step without adding execution data."""

    return {"activity_id": step.activity_id}


def document_content(document: PipelineDocument) -> JsonObject:
    """Serialize a complete pipeline for changelog snapshots."""

    return {
        "id": document.id,
        "title": document.title,
        "description": document.description,
        "enabled": document.enabled,
        "status": document.status,
        "steps": [step_content(step) for step in document.steps],
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }
