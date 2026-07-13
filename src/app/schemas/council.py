from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from .common import (
    CompositionSummaryResponse,
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResponseSchema,
)


class CouncilAssignmentSchema(RequestSchema):
    """Persona and skills assigned to one council role."""

    role: NonEmptyString
    persona_id: NonEmptyString
    skill_ids: list[NonEmptyString] = Field(min_length=1)


class CouncilCreateRequest(RequestSchema):
    """Request body for creating a council."""

    name: NonEmptyString
    description: str = ""
    assignments: list[CouncilAssignmentSchema] = Field(min_length=1)


class CouncilUpdateRequest(RequestSchema):
    """Request body for updating a council."""

    expected_version: PositiveInteger
    name: NonEmptyString | None = None
    description: str | None = None
    assignments: list[CouncilAssignmentSchema] | None = Field(
        default=None,
        min_length=1,
    )

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Require at least one mutable value."""

        values = (
            self.name,
            self.description,
            self.assignments,
        )

        if all(value is None for value in values):
            raise ValueError("At least one council field must be updated.")

        return self


class CouncilSummaryResponse(CompositionSummaryResponse):
    """Lightweight council returned by list operations."""


class CouncilAssignmentResponse(ResponseSchema):
    role: str
    persona_id: str
    skill_ids: list[str]


class CouncilResponse(ResponseSchema):
    """Complete council returned by describe and write operations."""

    id: str
    name: str
    description: str
    assignments: list[CouncilAssignmentResponse]
    version: PositiveInteger
    created_at: datetime
    updated_at: datetime


class CouncilListResponse(ListResponse[CouncilSummaryResponse]):
    """Response returned by the council list endpoint."""
