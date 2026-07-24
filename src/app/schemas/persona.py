"""HTTP schemas for persona resources."""

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
    """Request body for creating or copying a persona."""

    name: NonEmptyString | None = None
    description: str = ""
    instructions: NonEmptyString | None = None
    skill_ids: list[NonEmptyString] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_persona_id: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_creation_mode(self) -> Self:
        """Validate the fields required by direct and source-based creation."""

        self._require_unique_skill_ids()

        if self.source_persona_id is None:
            if self.name is None or self.instructions is None:
                raise ValueError(
                    "Name and instructions are required when creating a persona."
                )
            return self

        unsupported_overrides = {
            "description",
            "instructions",
            "skill_ids",
            "metadata",
        } & self.model_fields_set
        if unsupported_overrides:
            raise ValueError(
                "A persona copy only accepts source_persona_id and an optional name."
            )

        return self

    def _require_unique_skill_ids(self) -> None:
        """Reject ambiguous duplicate persona-skill associations."""

        if len(self.skill_ids) != len(set(self.skill_ids)):
            raise ValueError("Skill ids must be unique.")


class PersonaPatchRequest(RequestSchema):
    """Fields that may change for an available persona."""

    expected_version: PositiveInteger | None = None
    name: NonEmptyString | None = None
    description: str | None = None
    instructions: NonEmptyString | None = None
    skill_ids: list[NonEmptyString] | None = None
    metadata: dict[str, Any] | None = None
    enabled: StrictBool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        """Require a concrete change and version content modifications."""

        content_values = (
            self.name,
            self.description,
            self.instructions,
            self.skill_ids,
            self.metadata,
        )
        has_content_changes = any(
            value is not None
            for value in content_values
        )
        enabled_supplied = "enabled" in self.model_fields_set

        if not has_content_changes and not enabled_supplied:
            raise ValueError("At least one persona field must be updated.")
        if enabled_supplied and self.enabled is None:
            raise ValueError("Enabled must be true or false.")
        if has_content_changes and self.expected_version is None:
            raise ValueError(
                "Expected version is required when modifying persona content."
            )
        if (
            self.skill_ids is not None
            and len(self.skill_ids) != len(set(self.skill_ids))
        ):
            raise ValueError("Skill ids must be unique.")

        return self

    def has_content_changes(self) -> bool:
        """Return whether the request changes editable persona content."""

        return any(
            value is not None
            for value in (
                self.name,
                self.description,
                self.instructions,
                self.skill_ids,
                self.metadata,
            )
        )


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
    skill_ids: list[str]
    metadata: dict[str, Any]
    version: PositiveInteger
    created_at: datetime
    updated_at: datetime


class PersonaListResponse(ListResponse[PersonaSummaryResponse]):
    """Response returned by the persona list endpoint."""
