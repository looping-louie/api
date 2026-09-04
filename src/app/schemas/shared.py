"""Schemas and constrained values shared by HTTP resources."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from src.app.catalogs.persona_skills import InstructionOrigin


NonEmptyString = Annotated[
    str,
    Field(min_length=1),
]

ResourceName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=140,
        pattern=r'^[\p{L}\p{N}_][^.+?/<>*%&:\s]*$',
    ),
]

ResourceTitle = Annotated[
    str,
    Field(
        min_length=1,
        max_length=140,
        pattern=r'^[\p{L}\p{N}_][^.+?/<>*%&:\p{C}\p{Zl}\p{Zp}]*$',
    ),
]

PositiveInteger = Annotated[
    int,
    Field(gt=0, strict=True),
]

NonNegativeInteger = Annotated[
    int,
    Field(ge=0, strict=True),
]

StrictnessValue = Annotated[
    int,
    Field(ge=0, le=100, strict=True),
]


class RequestSchema(BaseModel):
    """Base configuration for API request schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ResponseSchema(BaseModel):
    """Base configuration for API response schemas."""

    model_config = ConfigDict(
        from_attributes=True,
    )


class ResourceSummaryResponse(ResponseSchema):
    """Fields shared by instruction resource summaries."""

    id: str
    name: str
    description: str
    version: PositiveInteger
    created_at: datetime
    updated_at: datetime


class InstructionCapabilitiesResponse(ResponseSchema):
    """Project-specific origin and action capabilities for an instruction."""

    origin: InstructionOrigin
    enabled: bool
    editable: bool
    duplicable: bool
    deprecated: bool
    catalog_version: PositiveInteger | None
    source_instruction_id: str | None


ItemType = TypeVar("ItemType")


class ListResponse(ResponseSchema, Generic[ItemType]):
    """Generic response envelope for list operations."""

    items: list[ItemType]
    total: NonNegativeInteger


class DeleteResponse(ResponseSchema):
    """Response returned after deleting a resource."""

    deleted: bool = True
