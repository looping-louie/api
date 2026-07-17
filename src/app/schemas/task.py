"""Task request/response schemas."""

from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.app.schemas.generator import GeneratorAssignment
from src.app.schemas.metrics import ModelMetrics
from src.app.schemas.plan import ProjectPhase
from src.app.schemas.project import ProjectProfile
from src.app.schemas.reviewer import ReviewerAssignment


class Task(BaseModel):
    """One task received from the caller."""

    id: str
    status: Literal['pending', 'done']
    prompt: str
    run_id: str | None = None
    commit_message: str


class CompletedTask(BaseModel):
    """One task completed during execution."""

    task_id: str
    run_id: str
    commit_sha: str
    commit_message: str
    phase: ProjectPhase
    reasoning: str
    generator: GeneratorAssignment
    reviewers: list[ReviewerAssignment]


class RunRequest(BaseModel):
    """
    Request model for the /task/run endpoint.

    Executes one task as a single atomic API call.
    """

    model_config = ConfigDict(extra='forbid')

    repo_path: str
    task: Task
    constitution: str
    project_profile: ProjectProfile
    max_iterations: int = 3
    generator_model: str = 'deepseek-ai/DeepSeek-V4-Pro'
    reviewer_model: str = 'gpt-4.1-mini'
    planner_model: str = 'gpt-4.1-mini'
    required_reviewer_skills: list[str] = Field(default_factory=list)
    generator_persona: str | None = None


class RunResponse(BaseModel):
    """Final response returned by the /task/run endpoint."""

    ok: bool
    status: Literal['completed', 'stopped']
    commit_allowed: bool = False

    completed: CompletedTask | None = None
    task_id: str | None = None
    run_id: str | None = None
    approved: bool | None = None
    message: str | None = None


TaskStatus = Literal[
    'in_progress',
    'completed',
    'stopped',
    'failed',
    'expired',
]

TaskAction = Literal[
    'collect_snapshot',
    'apply_operations',
    'submit_review_input',
    'commit_if_allowed',
    'none',
]

TaskErrorCode = Literal[
    'token_conflict',
    'token_expired',
    'invalid_transition',
    'invalid_action_result',
    'run_not_found',
    'run_cancelled',
]


class StartRequest(BaseModel):
    """Request model for POST /task/start."""

    model_config = ConfigDict(extra='forbid')

    repo_path: str
    task: Task
    constitution: str
    project_profile: ProjectProfile
    max_iterations: int = 3
    generator_model: str = 'deepseek-ai/DeepSeek-V4-Pro'
    reviewer_model: str = 'gpt-4.1-mini'
    planner_model: str = 'gpt-4.1-mini'
    required_reviewer_skills: list[str] = Field(default_factory=list)
    generator_persona: str | None = None


class WorkspaceMetadata(BaseModel):
    """Workspace metadata reported by CLI for one run."""

    workspace_path: str
    source_commit_sha: str


class CollectSnapshotActionResult(BaseModel):
    """CLI output for next_action=collect_snapshot."""

    action: Literal['collect_snapshot']
    repo_context: str
    workspace_metadata: WorkspaceMetadata


class ApplyOperationsActionResult(BaseModel):
    """CLI output for next_action=apply_operations."""

    action: Literal['apply_operations']
    applied: bool
    error: str | None = None
    final_diff: str | None = None
    changed_files: list[str] = Field(default_factory=list)


class SubmitReviewInputActionResult(BaseModel):
    """CLI output for next_action=submit_review_input."""

    action: Literal['submit_review_input']
    final_diff: str
    changed_file_contents: dict[str, str] = Field(default_factory=dict)


class CommitIfAllowedActionResult(BaseModel):
    """CLI output for next_action=commit_if_allowed."""

    action: Literal['commit_if_allowed']
    committed: bool
    commit_sha: str | None = None
    commit_message: str | None = None
    error: str | None = None


ContinueActionResult = (
    CollectSnapshotActionResult
    | ApplyOperationsActionResult
    | SubmitReviewInputActionResult
    | CommitIfAllowedActionResult
)


class ContinueRequest(BaseModel):
    """Request model for POST /task/continue."""

    model_config = ConfigDict(extra='forbid')

    run_id: str
    continuation_token: str
    idempotency_key: str
    action_result: ContinueActionResult


class ApplyOperationsPayload(BaseModel):
    """Payload returned by API when CLI must apply file operations."""

    operations: list[dict[str, Any]] = Field(default_factory=list)
    generator_metrics: ModelMetrics | None = None


class CheckpointPayload(BaseModel):
    """Optional checkpoint payload attached to a continuation response."""

    apply_operations: ApplyOperationsPayload | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class CheckpointResponse(BaseModel):
    """Shared response shape for start/continue/get task checkpoint endpoints."""

    ok: bool
    run_id: str
    iteration: int
    status: TaskStatus
    next_action: TaskAction
    continuation_token: str | None = None
    token_revision: int
    payload: CheckpointPayload | None = None
    commit_allowed: bool = False
    completed: CompletedTask | None = None
    error_code: TaskErrorCode | None = None
    message: str | None = None
    recoverable: bool | None = None


class StartResponse(CheckpointResponse):
    """Response model for POST /task/start."""


class ContinueResponse(CheckpointResponse):
    """Response model for POST /task/continue."""


class GetResponse(CheckpointResponse):
    """Response model for GET /task/{run_id}."""


__all__ = [
    'ApplyOperationsActionResult',
    'ApplyOperationsPayload',
    'CollectSnapshotActionResult',
    'CompletedTask',
    'CommitIfAllowedActionResult',
    'GetResponse',
    'RunRequest',
    'RunResponse',
    'StartRequest',
    'StartResponse',
    'ContinueRequest',
    'ContinueResponse',
    'CheckpointResponse',
    'ContinueActionResult',
    'SubmitReviewInputActionResult',
    'TaskAction',
    'CheckpointPayload',
    'TaskErrorCode',
    'TaskStatus',
    'Task',
    'WorkspaceMetadata',
]
