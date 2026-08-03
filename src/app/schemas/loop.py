"""HTTP request and response schemas for loop resources."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from .shared import (
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResponseSchema,
)


LoopFlowValue = Literal["direct", "refinement", "roundtable"]
LoopStatusValue = Literal["active", "disabled", "archived"]
LoopRoleValue = Literal["generator", "reviewer", "aggregator"]
LoopOutputTypeValue = Literal["text", "json", "files"]
LoopChangeTypeValue = Literal[
    "created",
    "updated",
    "enabled",
    "disabled",
    "archived",
    "deleted",
]


class LoopStopConditionsSchema(RequestSchema):
    """Optional positive limits, of which at least one is required."""

    max_iterations: PositiveInteger | None = None
    max_tokens: PositiveInteger | None = None
    timeout_seconds: PositiveInteger | None = None

    @model_validator(mode="after")
    def require_one_condition(self) -> Self:
        """Reject an object with no configured stop condition."""

        if all(
            value is None
            for value in (
                self.max_iterations,
                self.max_tokens,
                self.timeout_seconds,
            )
        ):
            raise ValueError("At least one stop condition is required.")
        return self


class LoopAgentSchema(RequestSchema):
    """Agent assignment accepted in loop writes."""

    id: NonEmptyString | None = None
    model_id: NonEmptyString
    persona_id: NonEmptyString
    role: LoopRoleValue


class LoopOutputContractSchema(RequestSchema):
    """Generic output contract accepted in loop writes."""

    type: LoopOutputTypeValue
    description: NonEmptyString
    files: list[NonEmptyString] = Field(default_factory=list)
    schema_: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        serialization_alias="schema",
    )

    @model_validator(mode="after")
    def validate_type_requirements(self) -> Self:
        """Require the data specific to files and JSON outputs."""

        if self.type == "files" and not self.files:
            raise ValueError("Files output requires at least one path.")
        if self.type == "json" and self.schema_ is None:
            raise ValueError("JSON output requires a schema.")
        return self


class LoopCreateRequest(RequestSchema):
    """Request body for creating a loop."""

    title: NonEmptyString
    description: str
    flow: LoopFlowValue
    stop_conditions: LoopStopConditionsSchema
    agents: list[LoopAgentSchema]
    output_contract: LoopOutputContractSchema


class LoopPatchRequest(RequestSchema):
    """Partial mutable loop fields accepted by PATCH."""

    title: NonEmptyString | None = None
    description: str | None = None
    flow: LoopFlowValue | None = None
    status: LoopStatusValue | None = None
    stop_conditions: LoopStopConditionsSchema | None = None
    agents: list[LoopAgentSchema] | None = None
    output_contract: LoopOutputContractSchema | None = None

    @model_validator(mode="after")
    def require_supplied_non_null_change(self) -> Self:
        """Reject empty requests and explicit null mutable fields."""

        if not self.model_fields_set:
            raise ValueError("At least one loop field must be supplied.")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null.")
        return self


class LoopStopConditionsResponse(ResponseSchema):
    """Stored loop stop conditions."""

    max_iterations: PositiveInteger | None
    max_tokens: PositiveInteger | None
    timeout_seconds: PositiveInteger | None


class LoopAgentResponse(ResponseSchema):
    """Stored loop agent with its generated identifier."""

    id: str
    model_id: str
    persona_id: str
    role: LoopRoleValue


class LoopOutputContractResponse(ResponseSchema):
    """Stored generic output contract."""

    type: LoopOutputTypeValue
    description: str
    files: list[str]
    schema_: dict[str, Any] | None = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )


class LoopResponse(ResponseSchema):
    """Complete loop representation."""

    id: str
    title: str
    description: str
    flow: LoopFlowValue
    status: LoopStatusValue
    stop_conditions: LoopStopConditionsResponse
    agents: list[LoopAgentResponse]
    output_contract: LoopOutputContractResponse
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class LoopListResponse(ListResponse[LoopResponse]):
    """Fixed-size offset page of loop definitions."""


class LoopChangelogEntryResponse(ResponseSchema):
    """One immutable loop changelog entry."""

    id: str
    loop_id: str
    change_type: LoopChangeTypeValue
    actor_id: str
    changed_at: datetime
    diff: dict[str, Any] | None
    content: dict[str, Any] | None


class LoopChangelogListResponse(
    ListResponse[LoopChangelogEntryResponse]
):
    """Fixed-size offset page of changelog entries."""
