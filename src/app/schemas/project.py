"""Project resource and profile schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.app.schemas.shared import NonEmptyString, RequestSchema, ResponseSchema


class ProjectCreateRequest(RequestSchema):
    """Fields required to create a User-owned Project."""

    name: NonEmptyString


class ProjectResponse(ResponseSchema):
    """Project identity visible through the current User's collection."""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class ProjectPatchRequest(RequestSchema):
    """Mutable fields for one Project."""

    name: NonEmptyString | None = None

    @model_validator(mode='after')
    def require_name(self) -> 'ProjectPatchRequest':
        """Require an explicit non-null Project name."""

        if 'name' not in self.model_fields_set or self.name is None:
            raise ValueError('Name must be supplied.')
        return self


class ProjectProfileMarkers(BaseModel):
    """Boolean repository markers used by the execution planner."""

    model_config = ConfigDict(extra='forbid')

    nuxt: bool
    package_json: bool
    fastapi: bool
    docker: bool
    tests: bool


class ProjectProfile(BaseModel):
    """Validated project profile payload provided by the caller."""

    model_config = ConfigDict(extra='forbid')

    source_file_count: int = Field(ge=0)
    approximate_source_chars: int = Field(ge=0)
    extension_counts: dict[str, int] = Field(default_factory=dict)
    top_level_entries: list[str] = Field(default_factory=list)
    markers: ProjectProfileMarkers


__all__ = [
    'ProjectCreateRequest',
    'ProjectPatchRequest',
    'ProjectProfile',
    'ProjectProfileMarkers',
    'ProjectResponse',
]
