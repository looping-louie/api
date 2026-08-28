"""Domain models for persisted activity executions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping


ActivityRunStatus = Literal['in_progress', 'failed', 'completed', 'stopped']
ActivityRunState = Literal[
    'awaiting_snapshot',
    'awaiting_generation',
    'awaiting_apply',
    'awaiting_review_input',
    'awaiting_commit',
    'awaiting_human_decision',
    'completed',
    'failed',
]
ActivityRunAction = Literal[
    'collect_snapshot',
    'apply_operations',
    'submit_review_input',
    'commit_if_allowed',
    'submit_human_decision',
    'none',
]


@dataclass(frozen=True, slots=True)
class ActivityRunDocument:
    """One workspace-scoped execution owned by an activity definition."""

    id: str
    project_id: str
    activity_id: str
    input: str
    status: ActivityRunStatus
    state: ActivityRunState
    next_action: ActivityRunAction
    iteration: int
    token_revision: int
    continuation_token: str | None
    activity_snapshot: Mapping[str, object]
    execution_context: Mapping[str, object]
    created_at: datetime
    created_by: str
    updated_at: datetime
