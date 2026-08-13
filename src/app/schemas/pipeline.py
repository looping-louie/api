"""HTTP request and response schemas for pipeline resources."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import model_validator

from src.app.schemas.activity import ActivityCreateRequest, ActivityResponse
from src.app.schemas.shared import (
    ListResponse,
    NonEmptyString,
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
class PipelineActivityStepRequest(ActivityCreateRequest):
    """Activity definition created as one persisted pipeline step."""


class PipelineCreateRequest(RequestSchema):
    """Request body for creating an enabled pipeline."""

    title: NonEmptyString
    description: str
    steps: list[PipelineActivityStepRequest]


class PipelinePatchRequest(RequestSchema):
    """Partial mutable pipeline fields accepted by PATCH."""

    title: NonEmptyString | None = None
    description: str | None = None
    enabled: bool | None = None
    steps: list[PipelineActivityStepRequest] | None = None

    @model_validator(mode="after")
    def require_supplied_non_null_change(self) -> Self:
        """Reject empty requests and explicit null mutable fields."""

        if not self.model_fields_set:
            raise ValueError("At least one pipeline field must be supplied.")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null.")
        return self


class PipelineResponse(ResponseSchema):
    """Pipeline representation with full Activity definitions for each step."""

    id: str
    title: str
    description: str
    enabled: bool
    steps: list[ActivityResponse]
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
