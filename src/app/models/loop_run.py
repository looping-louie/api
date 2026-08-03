"""Domain models for persisted loop executions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping


LoopRunStatus = Literal['in_progress', 'failed', 'completed', 'stopped']
LoopRunState = Literal['awaiting_snapshot', 'awaiting_generation']
LoopRunAction = Literal['collect_snapshot', 'none']


@dataclass(frozen=True, slots=True)
class LoopRunDocument:
    """One workspace-scoped execution of a loop definition."""

    id: str
    workspace_id: str
    loop_id: str
    input: str
    status: LoopRunStatus
    state: LoopRunState
    next_action: LoopRunAction
    iteration: int
    token_revision: int
    continuation_token: str | None
    loop_snapshot: Mapping[str, object]
    execution_context: Mapping[str, object]
    created_at: datetime
    created_by: str
    updated_at: datetime