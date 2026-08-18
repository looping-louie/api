"""HTTP schemas for persona resources."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import ConfigDict, Field, StrictBool, model_validator

from src.app.catalogs.instructions import CatalogInstructionCategory

from .shared import (
    InstructionCapabilitiesResponse,
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResourceName,
    ResourceSummaryResponse,
)


class PersonaMetadata(RequestSchema):
    """Structured and extensible metadata belonging to a persona."""

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    category: CatalogInstructionCategory | None = None


class LinkedServiceReference(RequestSchema):
    """Immutable linked-service identifier used by a persona."""

    type: Literal['LinkedServiceReference']
    reference_id: NonEmptyString


class PersonaLinkedServiceConfig(RequestSchema):
    """Model selected through a linked service."""

    model: NonEmptyString


class PersonaCreateRequest(RequestSchema):
    """Request body for creating a persona."""

    name: ResourceName
    description: str = ""
    instructions: NonEmptyString
    model: NonEmptyString | None = None
    linked_service: LinkedServiceReference | None = None
    config: PersonaLinkedServiceConfig | None = None
    skill_ids: list[NonEmptyString] = Field(default_factory=list)
    metadata: PersonaMetadata = Field(default_factory=PersonaMetadata)

    @model_validator(mode="after")
    def validate_creation(self) -> Self:
        """Reject ambiguous duplicate persona-skill associations."""

        self._require_unique_skill_ids()
        self._require_linked_service_selection()
        return self

    def _require_unique_skill_ids(self) -> None:
        """Reject ambiguous duplicate persona-skill associations."""

        if len(self.skill_ids) != len(set(self.skill_ids)):
            raise ValueError("Skill ids must be unique.")

    def _require_linked_service_selection(self) -> None:
        """Require linked-service reference and model configuration together."""

        if (self.linked_service is None) != (self.config is None):
            raise ValueError('Linked service and config must be supplied together.')
        if self.model is not None and self.linked_service is not None:
            raise ValueError(
                'Model cannot be supplied with a linked-service selection.'
            )


class PersonaPatchRequest(RequestSchema):
    """Fields that may change for an available persona."""

    expected_version: PositiveInteger | None = None
    name: ResourceName | None = None
    description: str | None = None
    instructions: NonEmptyString | None = None
    model: NonEmptyString | None = None
    linked_service: LinkedServiceReference | None = None
    config: PersonaLinkedServiceConfig | None = None
    skill_ids: list[NonEmptyString] | None = None
    metadata: PersonaMetadata | None = None
    enabled: StrictBool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        """Require a concrete change and version content modifications."""

        content_values = (
            self.name,
            self.description,
            self.instructions,
            self.model,
            self.linked_service,
            self.config,
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
        linked_service_supplied = 'linked_service' in self.model_fields_set
        config_supplied = 'config' in self.model_fields_set
        if linked_service_supplied != config_supplied:
            raise ValueError('Linked service and config must be supplied together.')
        if linked_service_supplied and (
            self.linked_service is None or self.config is None
        ):
            raise ValueError('Linked service and config must be non-null.')
        if self.model is not None and linked_service_supplied:
            raise ValueError(
                'Model cannot be supplied with a linked-service selection.'
            )

        return self

    def has_content_changes(self) -> bool:
        """Return whether the request changes editable persona content."""

        return any(
            value is not None
            for value in (
                self.name,
                self.description,
                self.instructions,
                self.model,
                self.linked_service,
                self.config,
                self.skill_ids,
                self.metadata,
            )
        )


class PersonaSummaryResponse(
    InstructionCapabilitiesResponse,
    ResourceSummaryResponse,
):
    """Lightweight persona returned by list operations."""

    model: str | None
    linked_service: LinkedServiceReference | None = None
    config: PersonaLinkedServiceConfig | None = None
    category: CatalogInstructionCategory | None = None


class PersonaResponse(InstructionCapabilitiesResponse):
    """Complete persona returned by describe and write operations."""

    id: str
    name: str
    description: str
    instructions: str
    model: str | None
    linked_service: LinkedServiceReference | None = None
    config: PersonaLinkedServiceConfig | None = None
    skill_ids: list[str]
    metadata: PersonaMetadata
    version: PositiveInteger
    created_at: datetime
    updated_at: datetime


class PersonaListResponse(ListResponse[PersonaSummaryResponse]):
    """Response returned by the persona list endpoint."""
