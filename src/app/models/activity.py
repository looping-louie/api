"""Domain models for persisted activity definitions and their changelog."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.app.models.changelog import JsonObject


ActivityStatus = Literal['active', 'disabled', 'archived']
ActivityType = Literal[
    'approval',
    'quiz',
    'direct_loop',
    'refinement_loop',
    'loop',
]
ActivityChangeType = Literal[
    'created', 'updated', 'enabled', 'disabled', 'archived', 'deleted'
]


@dataclass(frozen=True, slots=True)
class ActivityDocument:
    """Complete workspace-scoped activity definition."""

    id: str
    workspace_id: str
    title: str
    description: str
    status: ActivityStatus
    type: ActivityType
    config: JsonObject
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


@dataclass(frozen=True, slots=True)
class ActivityChangelogEntry:
    """Immutable record of one activity mutation."""

    id: str
    activity_id: str
    workspace_id: str
    change_type: ActivityChangeType
    actor_id: str
    changed_at: datetime
    diff: JsonObject | None
    content: JsonObject | None
