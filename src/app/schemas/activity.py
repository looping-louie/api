"""HTTP request and response schemas for activity resources."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from .loop import (
    LoopAgentSchema,
    LoopFlowValue,
    LoopOutputContractSchema,
    LoopStopConditionsSchema,
)
from .shared import ListResponse, NonEmptyString, RequestSchema, ResponseSchema


ActivityStatusValue = Literal['active', 'disabled', 'archived']
ActivityChangeTypeValue = Literal[
    'created', 'updated', 'enabled', 'disabled', 'archived', 'deleted'
]


class DirectLoopActivityConfig(RequestSchema):
    """Configuration for a direct loop activity."""

    type: Literal['direct_loop']
    stop_conditions: LoopStopConditionsSchema
    agents: list[LoopAgentSchema]
    output_contract: LoopOutputContractSchema


class LoopActivityConfig(RequestSchema):
    """Configuration for loop variants pending their own Activity type."""

    type: Literal['loop']
    flow: LoopFlowValue
    stop_conditions: LoopStopConditionsSchema
    agents: list[LoopAgentSchema]
    output_contract: LoopOutputContractSchema


class ApprovalActivityConfig(RequestSchema):
    """Configuration for an activity that requires human approval."""

    type: Literal['approval']


class QuizActivityConfig(RequestSchema):
    """Configuration for an activity that requires a human quiz response."""

    type: Literal['quiz']
    quiz: dict[str, Any]


ActivityConfig = Annotated[
    ApprovalActivityConfig
    | QuizActivityConfig
    | DirectLoopActivityConfig
    | LoopActivityConfig,
    Field(discriminator='type'),
]


class ActivityCreateRequest(RequestSchema):
    """Request body for creating an activity."""

    title: NonEmptyString
    description: str
    type: Literal['approval', 'quiz', 'direct_loop', 'loop']
    config: ActivityConfig

    @model_validator(mode='after')
    def require_matching_type(self) -> 'ActivityCreateRequest':
        """Keep the common activity type aligned with the config discriminator."""

        if self.type != self.config.type:
            raise ValueError('type must match config.type.')
        return self


class ActivityPatchRequest(RequestSchema):
    """Mutable activity fields accepted by PATCH."""

    title: NonEmptyString | None = None
    description: str | None = None
    status: ActivityStatusValue | None = None
    config: ActivityConfig | None = None

    @model_validator(mode='after')
    def require_supplied_non_null_change(self) -> 'ActivityPatchRequest':
        """Reject empty updates and explicit null values."""

        if not self.model_fields_set:
            raise ValueError('At least one activity field must be supplied.')
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f'{field_name} must not be null.')
        return self


class ActivityResponse(ResponseSchema):
    """Complete activity representation."""

    id: str
    workspace_id: str
    title: str
    description: str
    status: ActivityStatusValue
    type: Literal['approval', 'quiz', 'direct_loop', 'loop']
    config: ActivityConfig
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class ActivityListResponse(ListResponse[ActivityResponse]):
    """Fixed-size offset page of activities."""


class ActivityChangelogEntryResponse(ResponseSchema):
    """One immutable activity changelog entry."""

    id: str
    activity_id: str
    change_type: ActivityChangeTypeValue
    actor_id: str
    changed_at: datetime
    diff: dict[str, Any] | None
    content: dict[str, Any] | None


class ActivityChangelogListResponse(
    ListResponse[ActivityChangelogEntryResponse]
):
    """Fixed-size offset page of activity changelog entries."""
