"""Project profile schemas."""

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = ['ProjectProfile', 'ProjectProfileMarkers']
