"""Normalization and validation rules for complete pipelines."""

from __future__ import annotations

from src.app.models.changelog import JsonObject
from src.app.models.pipeline import (
    PipelineDocument,
    PipelineHumanGateStep,
    PipelineLoopStep,
    PipelineQuizConfig,
    PipelineStatus,
    PipelineStep,
)
from src.app.services.pipelines.types import (
    InvalidPipelineStepsError,
    PipelineQuizConfigInput,
    PipelineStepInput,
    UnsupportedHumanGateTypeError,
    UnsupportedPipelineStepError,
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
        steps.append(_normalize_step(value, position))
    return tuple(steps)


def _normalize_step(
    value: PipelineStepInput,
    position: int,
) -> PipelineStep:
    """Normalize one supported step while preserving its position."""

    if value.type == "loop":
        if value.gate_type is not None or value.config is not None:
            raise InvalidPipelineStepsError(
                field_name=f"steps.{position}",
                message="loop steps only accept loop_id",
            )
        return PipelineLoopStep(
            type="loop",
            loop_id=require_text(
                value.loop_id,
                f"steps.{position}.loop_id",
            ),
        )
    if value.type != "human_gate":
        raise UnsupportedPipelineStepError(step_type=value.type)
    if value.loop_id is not None:
        raise InvalidPipelineStepsError(
            field_name=f"steps.{position}",
            message="human gates do not accept loop_id",
        )
    return _normalize_gate(value, position)


def _normalize_gate(
    value: PipelineStepInput,
    position: int,
) -> PipelineHumanGateStep:
    """Normalize approval and quiz gate-specific configuration."""

    if value.gate_type == "approval":
        if value.config is not None:
            raise InvalidPipelineStepsError(
                field_name=f"steps.{position}.config",
                message="must not be supplied for approval gates",
            )
        return PipelineHumanGateStep(
            type="human_gate",
            gate_type="approval",
            config=None,
        )
    if value.gate_type != "quiz":
        raise UnsupportedHumanGateTypeError(gate_type=value.gate_type)
    if value.config is None:
        raise InvalidPipelineStepsError(
            field_name=f"steps.{position}.config",
            message="is required for quiz gates",
        )
    return PipelineHumanGateStep(
        type="human_gate",
        gate_type="quiz",
        config=_normalize_quiz_config(value.config, position),
    )


def _normalize_quiz_config(
    value: PipelineQuizConfigInput,
    position: int,
) -> PipelineQuizConfig:
    """Validate positive quiz limits and their cross-field invariant."""

    fields = {
        "minimum_correct_answers": value.minimum_correct_answers,
        "question_count": value.question_count,
        "option_count": value.option_count,
    }
    minimums = {
        "minimum_correct_answers": 1,
        "question_count": 1,
        "option_count": 2,
    }
    for field_name, field_value in fields.items():
        if (
            isinstance(field_value, bool)
            or not isinstance(field_value, int)
            or field_value < minimums[field_name]
        ):
            raise InvalidPipelineStepsError(
                field_name=f"steps.{position}.config.{field_name}",
                message=f"must be at least {minimums[field_name]}",
            )
    if value.minimum_correct_answers > value.question_count:
        raise InvalidPipelineStepsError(
            field_name=(
                f"steps.{position}.config.minimum_correct_answers"
            ),
            message="cannot exceed question_count",
        )
    return PipelineQuizConfig(**fields)


def step_content(step: PipelineStep) -> JsonObject:
    """Serialize one domain step without adding execution data."""

    if isinstance(step, PipelineLoopStep):
        return {"type": "loop", "loop_id": step.loop_id}
    content: JsonObject = {
        "type": "human_gate",
        "gate_type": step.gate_type,
    }
    if step.config is not None:
        content["config"] = {
            "minimum_correct_answers": (
                step.config.minimum_correct_answers
            ),
            "question_count": step.config.question_count,
            "option_count": step.config.option_count,
        }
    return content


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
