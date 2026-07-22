from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import ConfigDict, Field, model_validator

from .common import (
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResourceSummaryResponse,
    ResponseSchema,
    StrictnessValue,
)


class SkillDefaultStrictness(RequestSchema):
    """Default strictness values by project phase."""

    prototype: StrictnessValue | None = None
    mvp: StrictnessValue | None = None
    production: StrictnessValue | None = None


class SkillMetadata(RequestSchema):
    """Structured and extensible metadata belonging to a skill."""

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    applies_when: list[NonEmptyString] | None = Field(
        default=None,
        min_length=1,
    )
    default_strictness: SkillDefaultStrictness | None = None


class SkillCreateRequest(RequestSchema):
    """Request body for creating a skill."""

    name: NonEmptyString
    description: str = ""
    instructions: NonEmptyString
    metadata: SkillMetadata = Field(default_factory=SkillMetadata)


class SkillUpdateRequest(RequestSchema):
    """Request body for updating a skill."""

    expected_version: PositiveInteger
    name: NonEmptyString | None = None
    description: str | None = None
    instructions: NonEmptyString | None = None
    metadata: SkillMetadata | None = None

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
            raise ValueError("At least one skill field must be updated.")

        return self


class SkillSummaryResponse(ResourceSummaryResponse):
    """Lightweight skill returned by list operations."""


class SkillResponse(ResponseSchema):
    """Complete skill returned by describe and write operations."""

    id: str
    name: str
    description: str
    instructions: str
    metadata: SkillMetadata
    version: PositiveInteger
    created_at: datetime
    updated_at: datetime


class SkillListResponse(ListResponse[SkillSummaryResponse]):
    """Response returned by the skill list endpoint."""
