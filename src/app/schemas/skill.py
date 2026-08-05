"""HTTP schemas for skill resources."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import ConfigDict, Field, StrictBool, model_validator

from .shared import (
    InstructionCapabilitiesResponse,
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResourceSummaryResponse,
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
    """Request body for creating or copying a skill."""

    name: NonEmptyString | None = None
    description: str = ""
    instructions: NonEmptyString | None = None
    metadata: SkillMetadata = Field(default_factory=SkillMetadata)
    source_skill_id: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_creation_mode(self) -> Self:
        """Validate the fields required by direct and source-based creation."""

        if self.source_skill_id is None:
            if self.name is None or self.instructions is None:
                raise ValueError(
                    "Name and instructions are required when creating a skill."
                )
            return self

        unsupported_overrides = {
            "description",
            "instructions",
            "metadata",
        } & self.model_fields_set
        if unsupported_overrides:
            raise ValueError(
                "A skill copy only accepts source_skill_id and an optional name."
            )

        return self


class SkillPatchRequest(RequestSchema):
    """Fields that may change for an available skill."""

    expected_version: PositiveInteger | None = None
    name: NonEmptyString | None = None
    description: str | None = None
    instructions: NonEmptyString | None = None
    metadata: SkillMetadata | None = None
    enabled: StrictBool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        """Require a concrete change and version content modifications."""

        content_values = (
            self.name,
            self.description,
            self.instructions,
            self.metadata,
        )
        has_content_changes = any(
            value is not None
            for value in content_values
        )
        enabled_supplied = "enabled" in self.model_fields_set

        if not has_content_changes and not enabled_supplied:
            raise ValueError("At least one skill field must be updated.")
        if enabled_supplied and self.enabled is None:
            raise ValueError("Enabled must be true or false.")
        if has_content_changes and self.expected_version is None:
            raise ValueError(
                "Expected version is required when modifying skill content."
            )

        return self

    def has_content_changes(self) -> bool:
        """Return whether the request changes editable skill content."""

        return any(
            value is not None
            for value in (
                self.name,
                self.description,
                self.instructions,
                self.metadata,
            )
        )


class SkillSummaryResponse(
    InstructionCapabilitiesResponse,
    ResourceSummaryResponse,
):
    """Lightweight skill returned by list operations."""


class SkillResponse(InstructionCapabilitiesResponse):
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
