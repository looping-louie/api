"""HTTP schemas for reusable reviewer skills."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SkillCreateRequest(BaseModel):
    """Request payload for creating an organisation-owned skill."""

    skill_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillUpdateRequest(BaseModel):
    """Request payload for editing a custom or built-in skill."""

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillResponse(BaseModel):
    """Merged skill returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    skill_id: str
    name: str
    description: str
    content: str
    metadata: dict[str, Any]
    source: str
    base_skill_id: str | None
    editable: bool
    deleted: bool
    created_by: str | None
    created_at: datetime | None
    updated_by: str | None
    updated_at: datetime | None


class SkillSummaryResponse(BaseModel):
    """Compact skill representation used in list responses."""

    model_config = ConfigDict(from_attributes=True)

    skill_id: str
    name: str
    description: str
    source: str
    editable: bool
    deleted: bool
    updated_at: datetime | None
