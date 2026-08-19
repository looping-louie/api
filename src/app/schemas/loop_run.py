"""HTTP request and response schemas for loop executions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .project import ProjectProfile

from .shared import (
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResponseSchema,
)


LoopRunStatusValue = Literal['in_progress', 'failed', 'completed', 'stopped']
LoopRunStateValue = Literal[
    'awaiting_snapshot',
    'awaiting_generation',
    'awaiting_apply',
    'awaiting_review_input',
    'awaiting_commit',
    'completed',
    'failed',
]
LoopRunActionValue = Literal['collect_snapshot', 'apply_operations', 'submit_review_input', 'commit_if_allowed', 'none']


class LoopRunCreateRequest(RequestSchema):
    """User input that starts one execution of the selected loop."""

    input: NonEmptyString


class LoopRunWorkspaceMetadata(RequestSchema):
    """Local repository metadata captured by the CLI."""

    workspace_path: NonEmptyString
    source_commit_sha: NonEmptyString


class LoopRunCollectSnapshotResult(RequestSchema):
    """CLI-owned local context supplied before loop generation begins."""

    action: Literal['collect_snapshot']
    repo_context: NonEmptyString
    workspace_metadata: LoopRunWorkspaceMetadata
    constitution: str
    project_profile: ProjectProfile


class LoopRunApplyOperationsResult(RequestSchema):
    """Result of applying API-planned file operations locally."""

    action: Literal['apply_operations']
    applied: bool
    final_diff: str = ''
    changed_files: list[str] = Field(default_factory=list)
    error: str | None = None


class LoopRunReviewInputResult(RequestSchema):
    """Local diff and changed contents supplied to configured reviewers."""

    action: Literal['submit_review_input']
    final_diff: str
    changed_file_contents: dict[str, str] = Field(default_factory=dict)


class LoopRunCommitResult(RequestSchema):
    """Outcome of the CLI-owned commit attempt."""

    action: Literal['commit_if_allowed']
    committed: bool
    commit_sha: str | None = None
    commit_message: str | None = None
    error: str | None = None


class LoopRunContinueRequest(RequestSchema):
    """One idempotent checkpoint continuation request."""

    pipeline_run_id: str | None = None
    lease_token: str | None = None
    continuation_token: NonEmptyString
    idempotency_key: NonEmptyString
    result: dict


class LoopRunResponse(ResponseSchema):
    """Persisted loop execution awaiting its first CLI checkpoint."""

    id: str
    loop_id: str
    input: str
    status: LoopRunStatusValue
    state: LoopRunStateValue
    next_action: LoopRunActionValue
    iteration: PositiveInteger
    token_revision: int
    continuation_token: str | None
    created_at: datetime
    created_by: str
    updated_at: datetime
    payload: dict[str, object] = Field(default_factory=dict)


class LoopRunListResponse(ListResponse[LoopRunResponse]):
    """Fixed-size offset page of loop executions."""


class ActivityRunResponse(ResponseSchema):
    """Persisted execution owned by one activity."""

    id: str
    activity_id: str
    input: str
    status: LoopRunStatusValue
    state: LoopRunStateValue
    next_action: LoopRunActionValue
    iteration: PositiveInteger
    token_revision: int
    continuation_token: str | None
    created_at: datetime
    created_by: str
    updated_at: datetime
    payload: dict[str, object] = Field(default_factory=dict)


class ActivityRunListResponse(ListResponse[ActivityRunResponse]):
    """Fixed-size offset page of activity executions."""
