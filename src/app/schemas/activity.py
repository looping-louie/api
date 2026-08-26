"""HTTP request and response schemas for activity resources."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self

from pydantic import Field, model_validator
from .execution import (
    HarnessRequest,
    HarnessResponse,
)
from .shared import (
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResourceName,
    ResponseSchema,
)


ActivityStatusValue = Literal['active', 'disabled', 'archived']
ActivityChangeTypeValue = Literal[
    'created', 'updated', 'enabled', 'disabled', 'archived', 'deleted'
]
ActivityTypeValue = Literal[
    'approval',
    'quiz',
    'direct_loop',
    'refinement_loop',
    'roundtable_loop',
]

LoopActivityRoleValue = Literal['generator', 'reviewer', 'aggregator']
LoopActivityOutputTypeValue = Literal['text', 'json', 'files']


class LoopActivityStopConditionsSchema(RequestSchema):
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


class LoopActivityAgentSchema(RequestSchema):
    """One Persona role and optional logical model override for a loop Activity."""

    id: NonEmptyString | None = None
    model_id: NonEmptyString | None = None
    persona_id: NonEmptyString
    role: LoopActivityRoleValue


class LoopActivityOutputContractSchema(RequestSchema):
    """Expected artifact format for a loop Activity."""

    type: LoopActivityOutputTypeValue
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


class DirectLoopActivityConfig(RequestSchema):
    """Configuration for a direct loop activity."""

    stop_conditions: LoopActivityStopConditionsSchema
    agents: list[LoopActivityAgentSchema]
    output_contract: LoopActivityOutputContractSchema

    @model_validator(mode='after')
    def validate_roles(self) -> 'DirectLoopActivityConfig':
        """Require one generator and no review or aggregation roles."""

        counts = _role_counts(self.agents)
        if counts != {'generator': 1, 'reviewer': 0, 'aggregator': 0}:
            raise ValueError('Direct loop requires exactly one generator only.')
        return self


class RefinementLoopActivityConfig(RequestSchema):
    """Configuration for a refinement loop activity."""

    stop_conditions: LoopActivityStopConditionsSchema
    agents: list[LoopActivityAgentSchema]
    output_contract: LoopActivityOutputContractSchema

    @model_validator(mode='after')
    def validate_roles(self) -> 'RefinementLoopActivityConfig':
        """Require one generator, one or more reviewers, and no aggregator."""

        counts = _role_counts(self.agents)
        if counts['generator'] != 1 or counts['reviewer'] < 1 or counts['aggregator']:
            raise ValueError('Refinement loop requires one generator and one or more reviewers only.')
        return self


class RoundtableLoopActivityConfig(RequestSchema):
    """Configuration for a roundtable loop activity."""

    stop_conditions: LoopActivityStopConditionsSchema
    agents: list[LoopActivityAgentSchema]
    output_contract: LoopActivityOutputContractSchema

    @model_validator(mode='after')
    def validate_roles(self) -> 'RoundtableLoopActivityConfig':
        """Require multiple generators, one aggregator, and no reviewers."""

        counts = _role_counts(self.agents)
        if counts['generator'] < 2 or counts['reviewer'] or counts['aggregator'] != 1:
            raise ValueError('Roundtable loop requires two or more generators and one aggregator only.')
        return self


def _role_counts(agents: list[LoopActivityAgentSchema]) -> dict[str, int]:
    """Count each supported agent role for loop-cardinality validation."""

    return {
        role: sum(agent.role == role for agent in agents)
        for role in ('generator', 'reviewer', 'aggregator')
    }


class ApprovalActivityConfig(RequestSchema):
    """Configuration for an activity that requires human approval."""


class QuizActivityConfig(RequestSchema):
    """Configuration for an activity that requires a human quiz response."""

    quiz: dict[str, Any]


ActivityConfig = (
    ApprovalActivityConfig
    | QuizActivityConfig
    | DirectLoopActivityConfig
    | RefinementLoopActivityConfig
    | RoundtableLoopActivityConfig
)

ACTIVITY_CONFIG_SCHEMAS = {
    'approval': ApprovalActivityConfig,
    'quiz': QuizActivityConfig,
    'direct_loop': DirectLoopActivityConfig,
    'refinement_loop': RefinementLoopActivityConfig,
    'roundtable_loop': RoundtableLoopActivityConfig,
}


def validate_activity_config(
    *,
    activity_type: ActivityTypeValue,
    value: object,
) -> ActivityConfig:
    """Validate one configuration using its parent Activity type."""

    return ACTIVITY_CONFIG_SCHEMAS[activity_type].model_validate(value)


class ActivityCreateRequest(RequestSchema):
    """Request body for creating an activity."""

    name: ResourceName
    description: str
    type: ActivityTypeValue
    config: ActivityConfig
    model_id: NonEmptyString | None = None
    harness: HarnessRequest | None = None

    @model_validator(mode='before')
    @classmethod
    def validate_config_for_type(cls, value: object) -> object:
        """Use the top-level Activity type to select the config schema."""

        if (
            not isinstance(value, dict)
            or value.get('type') not in ACTIVITY_CONFIG_SCHEMAS
        ):
            return value
        normalized = dict(value)
        normalized['config'] = validate_activity_config(
            activity_type=value['type'],
            value=value.get('config'),
        )
        return normalized


class ActivityPatchRequest(RequestSchema):
    """Mutable activity fields accepted by PATCH."""

    name: ResourceName | None = None
    description: str | None = None
    status: ActivityStatusValue | None = None
    config: dict[str, Any] | None = None
    model_id: NonEmptyString | None = None
    harness: HarnessRequest | None = None

    @model_validator(mode='after')
    def require_supplied_non_null_change(self) -> 'ActivityPatchRequest':
        """Reject empty updates and explicit null values."""

        if not self.model_fields_set:
            raise ValueError('At least one activity field must be supplied.')
        for field_name in self.model_fields_set - {'model_id', 'harness'}:
            if getattr(self, field_name) is None:
                raise ValueError(f'{field_name} must not be null.')
        return self


class ActivityResponse(ResponseSchema):
    """Complete activity representation."""

    id: str
    workspace_id: str | None
    name: str
    description: str
    status: ActivityStatusValue
    type: ActivityTypeValue
    config: ActivityConfig
    model_id: str | None
    harness: HarnessResponse | None
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
