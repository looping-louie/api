"""Internal domain models for reusable reviewer skills."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class BuiltinSkill:
    """Skill loaded from a version-controlled Markdown file."""

    skill_id: str
    name: str
    description: str
    content: str
    metadata: dict[str, Any]
    file_path: str


@dataclass
class StoredSkill:
    """Organisation-owned custom skill, override or deletion marker."""

    id: str
    org_id: str
    skill_id: str
    name: str
    description: str
    content: str
    metadata: dict[str, Any]
    source: str
    base_skill_id: str | None
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True)
class SkillState:
    """Merged skill representation safe to return through the API."""

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
