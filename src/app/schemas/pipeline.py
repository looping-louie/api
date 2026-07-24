"""HTTP request and response schemas for pipeline resources."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from src.app.schemas.common import (
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResponseSchema,
)


PipelineStatusValue = Literal["active", "disabled", "archived"]
PipelineChangeTypeValue = Literal[
    "created",
    "updated",
    "enabled",
    "disabled",
    "archived",
]
OptionCount = Annotated[int, Field(ge=2, strict=True)]


class PipelineQuizConfigRequest(RequestSchema):
    """Required quiz threshold with default question and option counts."""

    minimum_correct_answers: PositiveInteger
    question_count: PositiveInteger = 10
    option_count: OptionCount = 3

    @model_validator(mode="after")
    def validate_threshold(self) -> Self:
        """Reject thresholds that cannot be met by the quiz."""

        if self.minimum_correct_answers > self.question_count:
            raise ValueError(
                "minimum_correct_answers cannot exceed question_count."
            )
        return self


class PipelineLoopStepRequest(RequestSchema):
    """Reference to an existing active loop."""

    type: Literal["loop"]
    loop_id: NonEmptyString


class PipelineHumanGateStepRequest(RequestSchema):
    """Approval or configured quiz human checkpoint."""

    type: Literal["human_gate"]
    gate_type: Literal["approval", "quiz"]
    config: PipelineQuizConfigRequest | None = None

    @model_validator(mode="after")
    def validate_gate_config(self) -> Self:
        """Require quiz configuration and forbid approval configuration."""

        if self.gate_type == "quiz" and self.config is None:
            raise ValueError("config is required for quiz gates.")
        if self.gate_type == "approval" and self.config is not None:
            raise ValueError(
                "config must not be supplied for approval gates."
            )
        return self


PipelineStepRequest = Annotated[
    PipelineLoopStepRequest | PipelineHumanGateStepRequest,
    Field(discriminator="type"),
]


class PipelineCreateRequest(RequestSchema):
    """Request body for creating an enabled pipeline."""

    title: NonEmptyString
    description: str
    steps: list[PipelineStepRequest]


class PipelinePatchRequest(RequestSchema):
    """Partial mutable pipeline fields accepted by PATCH."""

    title: NonEmptyString | None = None
    description: str | None = None
    enabled: bool | None = None
    steps: list[PipelineStepRequest] | None = None

    @model_validator(mode="after")
    def require_supplied_non_null_change(self) -> Self:
        """Reject empty requests and explicit null mutable fields."""

        if not self.model_fields_set:
            raise ValueError("At least one pipeline field must be supplied.")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null.")
        return self


class PipelineQuizConfigResponse(ResponseSchema):
    """Stored quiz-generation limits."""

    minimum_correct_answers: int
    question_count: int
    option_count: int


class PipelineLoopStepResponse(ResponseSchema):
    """Stored loop reference."""

    type: Literal["loop"]
    loop_id: str


class PipelineHumanGateStepResponse(ResponseSchema):
    """Stored human checkpoint."""

    type: Literal["human_gate"]
    gate_type: Literal["approval", "quiz"]
    config: PipelineQuizConfigResponse | None = None


PipelineStepResponse = Annotated[
    PipelineLoopStepResponse | PipelineHumanGateStepResponse,
    Field(discriminator="type"),
]


class PipelineResponse(ResponseSchema):
    """Complete public pipeline definition."""

    id: str
    title: str
    description: str
    enabled: bool
    steps: list[PipelineStepResponse]
    created_at: datetime
    updated_at: datetime


class PipelineListResponse(ListResponse[PipelineResponse]):
    """Fixed-size offset page of pipeline definitions."""


class PipelineChangelogEntryResponse(ResponseSchema):
    """One immutable pipeline changelog entry."""

    id: str
    pipeline_id: str
    change_type: PipelineChangeTypeValue
    actor_id: str
    changed_at: datetime
    diff: dict[str, object] | None
    content: dict[str, object] | None


class PipelineChangelogListResponse(
    ListResponse[PipelineChangelogEntryResponse]
):
    """Fixed-size offset page of pipeline changelog entries."""
