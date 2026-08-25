"""HTTP request and response schemas for pipeline resources."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from src.app.schemas.activity import ActivityCreateRequest, ActivityResponse
from src.app.schemas.activity_run import ActivityRunResponse
from src.app.schemas.execution import (
    HarnessRequest,
    HarnessResponse,
    ModelTargetRequest,
    ModelTargetResponse,
)
from src.app.schemas.shared import (
    ListResponse,
    NonEmptyString,
    RequestSchema,
    ResourceName,
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


class PipelineHarnessRequest(RequestSchema):
    """One supported Pipeline Harness selection."""

    kind: Literal['louie', 'codex_cli'] = 'louie'
    version: Literal['v1'] = 'v1'
    config: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode='after')
    def require_empty_harness_config(self) -> 'PipelineHarnessRequest':
        """Reject settings not supported by the initial Harness contract."""

        if self.config:
            raise ValueError(f'{self.kind} harness config must be empty.')
        return self


class PipelineHarnessResponse(ResponseSchema):
    """The persisted Harness selection for a Pipeline."""

    kind: Literal['louie', 'codex_cli']
    version: Literal['v1']
    config: dict[str, object]


class PipelineStepDependencyRequest(RequestSchema):
    """One named Activity condition required by a pipeline step."""

    activity: NonEmptyString
    condition: Literal['success', 'failure']


class PipelineStepDependencyResponse(ResponseSchema):
    """One named Activity condition returned for a pipeline step."""

    activity: str
    condition: Literal['success', 'failure']


class PipelineActivityStepRequest(ActivityCreateRequest):
    """Activity definition created as one persisted pipeline step."""

    depends_on: list[PipelineStepDependencyRequest] = Field(
        default_factory=list,
        validation_alias='dependsOn',
        serialization_alias='dependsOn',
    )


class PipelineCreateRequest(RequestSchema):
    """Request body for creating an enabled pipeline."""

    name: ResourceName
    description: str
    steps: list[PipelineActivityStepRequest]
    model_target: ModelTargetRequest | None = None
    harness: PipelineHarnessRequest | None = None


class PipelinePatchRequest(RequestSchema):
    """Partial mutable pipeline fields accepted by PATCH."""

    name: ResourceName | None = None
    description: str | None = None
    enabled: bool | None = None
    steps: list[PipelineActivityStepRequest] | None = None
    model_target: ModelTargetRequest | None = None
    harness: PipelineHarnessRequest | None = None

    @model_validator(mode="after")
    def require_supplied_non_null_change(self) -> Self:
        """Reject empty requests and explicit null mutable fields."""

        if not self.model_fields_set:
            raise ValueError("At least one pipeline field must be supplied.")
        for field_name in self.model_fields_set - {'model_target', 'harness'}:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null.")
        return self


class PipelineActivityStepResponse(ActivityResponse):
    """Pipeline Activity with its graph dependencies."""

    depends_on: list[PipelineStepDependencyResponse] = Field(
        default_factory=list,
        serialization_alias='dependsOn',
    )


class PipelineResponse(ResponseSchema):
    """Pipeline representation with full Activity definitions for each step."""

    id: str
    name: str
    description: str
    enabled: bool
    model_target: ModelTargetResponse | None
    harness: PipelineHarnessResponse | None
    steps: list[PipelineActivityStepResponse]
    created_at: datetime
    updated_at: datetime


class PipelineListResponse(ListResponse[PipelineResponse]):
    """Fixed-size offset page of pipeline definitions."""


PipelineRunStatusValue = Literal[
    'prepared', 'queued', 'claimed', 'in_progress', 'waiting', 'failed', 'completed'
]
PipelineRunCommitModeValue = Literal['allow', 'forbid']
PipelineRunStepStatusValue = Literal[
    'pending', 'in_progress', 'completed', 'failed', 'skipped'
]


class PipelineRunCreateRequest(RequestSchema):
    """Input used for each activity scheduled by a new pipeline run."""

    input: NonEmptyString
    commit_mode: PipelineRunCommitModeValue = 'allow'


class PipelineRunClaimRequest(RequestSchema):
    """Worker identity and target status for a conditional run claim."""

    worker_id: NonEmptyString
    status: Literal['claimed']


class PipelineRunLeaseRenewRequest(RequestSchema):
    """Active worker token required to extend a claimed Pipeline run lease."""

    lease_token: NonEmptyString


class PipelineRunContinueRequest(RequestSchema):
    """Worker token required only when continuing a runtime-owned child run."""

    lease_token: NonEmptyString | None = None


class PipelineRunStepResponse(ResponseSchema):
    """Current outcome of one frozen pipeline step."""

    activity_id: str
    status: PipelineRunStepStatusValue
    activity_run_id: str | None


class PipelineRunEventResponse(ResponseSchema):
    """One immutable event in a Pipeline-run execution ledger."""

    id: str
    event_type: str
    activity_id: str | None
    actor_id: str
    payload: dict[str, object]
    created_at: datetime


class PipelineRunEventListResponse(ListResponse[PipelineRunEventResponse]):
    """All events recorded for one Pipeline execution."""


class PipelineRunResponse(ResponseSchema):
    """Durable pipeline execution and its currently selected child run."""

    id: str
    pipeline_id: str
    input: str
    commit_mode: PipelineRunCommitModeValue
    status: PipelineRunStatusValue
    current_activity_run: ActivityRunResponse | None
    steps: list[PipelineRunStepResponse]
    created_at: datetime
    created_by: str
    updated_at: datetime


class PipelineRunClaimResponse(ResponseSchema):
    """One worker-owned pipeline run and its secret lease token."""

    run: PipelineRunResponse
    lease_token: str | None


class PipelineRunClaimableResponse(ResponseSchema):
    """One claimable run with the entity tag required to claim it."""

    run: PipelineRunResponse
    etag: str


class PipelineRunClaimableListResponse(
    ListResponse[PipelineRunClaimableResponse]
):
    """Claimable pipeline runs owned by one active Pipeline."""


class PipelineRunLeaseResponse(ResponseSchema):
    """Current expiration returned after a successful worker lease renewal."""

    lease_expires_at: datetime


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
