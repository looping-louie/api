"""HTTP request and response schemas for loop executions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from .project import ProjectProfile

from .shared import (
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResponseSchema,
)


LoopRunStatusValue = Literal['in_progress', 'failed', 'completed', 'stopped']
LoopRunStateValue = Literal['awaiting_snapshot', 'awaiting_generation']
LoopRunActionValue = Literal['collect_snapshot', 'none']


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


class LoopRunContinueRequest(RequestSchema):
    """One idempotent checkpoint continuation request."""

    continuation_token: NonEmptyString
    idempotency_key: NonEmptyString
    result: LoopRunCollectSnapshotResult


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


class LoopRunListResponse(ListResponse[LoopRunResponse]):
    """Fixed-size offset page of loop executions."""