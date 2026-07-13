from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from .common import (
    CompositionSummaryResponse,
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResponseSchema,
)


class LoopModelBindingSchema(RequestSchema):
    """Model assigned to one role in a loop."""

    role: NonEmptyString
    model_id: NonEmptyString


class LoopModelBindingResponse(ResponseSchema):
    role: str
    model_id: str


class LoopCreateRequest(RequestSchema):
    """Request body for creating a loop."""

    name: NonEmptyString
    description: str = ""
    council_id: NonEmptyString
    max_iterations: PositiveInteger
    model_bindings: list[LoopModelBindingSchema] = Field(min_length=1)


class LoopUpdateRequest(RequestSchema):
    """Request body for updating a loop."""

    expected_version: PositiveInteger
    name: NonEmptyString | None = None
    description: str | None = None
    council_id: NonEmptyString | None = None
    max_iterations: PositiveInteger | None = None
    model_bindings: list[LoopModelBindingSchema] | None = Field(
        default=None,
        min_length=1,
    )

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Require at least one mutable value."""

        values = (
            self.name,
            self.description,
            self.council_id,
            self.max_iterations,
            self.model_bindings,
        )

        if all(value is None for value in values):
            raise ValueError("At least one loop field must be updated.")

        return self


class LoopSummaryResponse(CompositionSummaryResponse):
    """Lightweight loop returned by list operations."""


class LoopResponse(ResponseSchema):
    """Complete loop returned by describe and write operations."""

    id: str
    name: str
    description: str
    council_id: str
    max_iterations: PositiveInteger
    model_bindings: list[LoopModelBindingResponse]
    version: PositiveInteger
    created_at: datetime
    updated_at: datetime


class LoopListResponse(ListResponse[LoopSummaryResponse]):
    """Response returned by the loop list endpoint."""


class LoopValidationResponse(ResponseSchema):
    """Response returned when a stored loop is valid."""

    valid: Literal[True] = True
    loop: LoopResponse
