"""Schema values shared by loop-type Activity configurations."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import Field, model_validator

from .execution import ModelTargetRequest
from .shared import NonEmptyString, PositiveInteger, RequestSchema


ActivityLoopRoleValue = Literal['generator', 'reviewer', 'aggregator']
ActivityLoopOutputTypeValue = Literal['text', 'json', 'files']


class ActivityLoopStopConditionsSchema(RequestSchema):
    """Positive loop execution limits with at least one configured value."""

    max_iterations: PositiveInteger | None = None
    max_tokens: PositiveInteger | None = None
    timeout_seconds: PositiveInteger | None = None

    @model_validator(mode='after')
    def require_one_condition(self) -> Self:
        """Reject configurations with no stopping limit."""

        if all(
            value is None
            for value in (
                self.max_iterations,
                self.max_tokens,
                self.timeout_seconds,
            )
        ):
            raise ValueError('At least one stop condition is required.')
        return self


class ActivityLoopAgentSchema(RequestSchema):
    """One Persona role and optional explicit model target for a loop Activity."""

    id: NonEmptyString | None = None
    model_target: ModelTargetRequest | None = None
    persona_id: NonEmptyString
    role: ActivityLoopRoleValue


class ActivityLoopOutputContractSchema(RequestSchema):
    """Expected artifact format for a loop Activity."""

    type: ActivityLoopOutputTypeValue
    description: NonEmptyString
    files: list[NonEmptyString] = Field(default_factory=list)
    schema_: dict[str, Any] | None = Field(
        default=None,
        alias='schema',
        serialization_alias='schema',
    )

    @model_validator(mode='after')
    def validate_type_requirements(self) -> Self:
        """Require data specific to files and JSON outputs."""

        if self.type == 'files' and not self.files:
            raise ValueError('Files output requires at least one path.')
        if self.type == 'json' and self.schema_ is None:
            raise ValueError('JSON output requires a schema.')
        return self
