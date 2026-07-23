from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import Field, StrictBool, model_validator

from .common import (
    InstructionCapabilitiesResponse,
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResourceSummaryResponse,
)


class PersonaCreateRequest(RequestSchema):
    """Request body for creating a persona."""

    name: NonEmptyString
    description: str = ""
    instructions: NonEmptyString
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonaUpdateRequest(RequestSchema):
    """Request body for updating a persona."""

    expected_version: PositiveInteger
    name: NonEmptyString | None = None
    description: str | None = None
    instructions: NonEmptyString | None = None
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Require at least one mutable value."""

        values = (
            self.name,
            self.description,
            self.instructions,
            self.metadata,
        )

        if all(value is None for value in values):
            raise ValueError("At least one persona field must be updated.")

        return self


class PersonaEnabledRequest(RequestSchema):
    """Request body for changing effective workspace enablement."""

    enabled: StrictBool


class PersonaDuplicateRequest(RequestSchema):
    """Optional overrides used when forking an available persona."""

    name: NonEmptyString | None = None


class PersonaSummaryResponse(
    InstructionCapabilitiesResponse,
    ResourceSummaryResponse,
):
    """Lightweight persona returned by list operations."""


class PersonaResponse(InstructionCapabilitiesResponse):
    """Complete persona returned by describe and write operations."""

    id: str
    name: str
    description: str
    instructions: str
    metadata: dict[str, Any]
    version: PositiveInteger
    created_at: datetime
    updated_at: datetime


class PersonaListResponse(ListResponse[PersonaSummaryResponse]):
    """Response returned by the persona list endpoint."""
