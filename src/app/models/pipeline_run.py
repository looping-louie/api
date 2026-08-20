"""Domain models for persisted pipeline executions and their steps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping


PipelineRunStatus = Literal['queued', 'claimed', 'in_progress', 'failed', 'completed']
PipelineRunCommitMode = Literal['allow', 'forbid']
PipelineRunStepStatus = Literal[
    'pending',
    'in_progress',
    'completed',
    'failed',
    'skipped',
]


@dataclass(frozen=True, slots=True)
class PipelineRunStepDocument:
    """One frozen pipeline step and its optional child activity run."""

    position: int
    activity_id: str
    status: PipelineRunStepStatus
    activity_run_id: str | None
    activity_snapshot: Mapping[str, object]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PipelineRunDocument:
    """One workspace-scoped execution of a frozen pipeline definition."""

    id: str
    workspace_id: str
    pipeline_id: str
    input: str
    status: PipelineRunStatus
    worker_id: str | None
    lease_token: str | None
    lease_expires_at: datetime | None
    attempt: int
    current_activity_run_id: str | None
    pipeline_snapshot: Mapping[str, object]
    steps: tuple[PipelineRunStepDocument, ...]
    created_at: datetime
    created_by: str
    updated_at: datetime
    commit_mode: PipelineRunCommitMode = 'allow'
