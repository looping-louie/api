"""Domain models for persisted activity definitions and their changelog."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from src.app.models.changelog import JsonObject

if TYPE_CHECKING:
    from src.app.models.pipeline import PipelineHarness


ActivityStatus = Literal['active', 'disabled', 'archived']
ActivityType = Literal[
    'approval',
    'quiz',
    'direct_loop',
    'refinement_loop',
    'roundtable_loop',
]
ActivityChangeType = Literal[
    'created', 'updated', 'enabled', 'disabled', 'archived', 'deleted'
]


@dataclass(frozen=True, slots=True)
class ActivityDocument:
    """Complete User-owned Activity definition."""

    id: str
    workspace_id: str | None
    name: str
    description: str
    status: ActivityStatus
    type: ActivityType
    config: JsonObject
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    model_id: str | None = None
    harness: PipelineHarness | None = None
    user_id: str = ''

    def __post_init__(self) -> None:
        """Use the creator as owner for legacy in-memory construction."""

        if not self.user_id:
            object.__setattr__(self, 'user_id', self.created_by)


@dataclass(frozen=True, slots=True)
class ActivityChangelogEntry:
    """Immutable record of one activity mutation."""

    id: str
    activity_id: str
    workspace_id: str | None
    change_type: ActivityChangeType
    actor_id: str
    changed_at: datetime
    diff: JsonObject | None
    content: JsonObject | None
    user_id: str = ''

    def __post_init__(self) -> None:
        """Use the mutation actor as owner for legacy in-memory construction."""

        if not self.user_id:
            object.__setattr__(self, 'user_id', self.actor_id)
