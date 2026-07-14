"""Task request/response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.app.schemas.plan import ExecutionPlan
from src.app.schemas.project import ProjectProfile
from src.app.schemas.reviewer import ReviewerMetrics, ReviewerResult
from src.app.schemas.workflow import CompletedTask, Task


class RunRequest(BaseModel):
    """
    Request model for the /task/run endpoint.

    Executes one task as a single atomic API call.

    Transitional note:
    This contract is kept while harness execution still exists in API.
    If migration is aborted, this remains the primary task contract.
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

    completed: CompletedTask | None = None
    task_id: str | None = None
    run_id: str | None = None
    approved: bool | None = None
    message: str | None = None


class PlanRequest(BaseModel):
    """Request model for the /task/plan endpoint."""

    model_config = ConfigDict(extra='forbid')

    task_id: str | None = None
    prompt: str
    constitution: str
    project_profile: ProjectProfile
    planner_model: str = 'gpt-4.1-mini'
    required_reviewer_skills: list[str] = Field(default_factory=list)
    generator_persona: str | None = None


class PlanResponse(BaseModel):
    """Response model for the /task/plan endpoint."""

    ok: bool
    task_id: str | None = None
    execution_plan: ExecutionPlan


class ChangedFile(BaseModel):
    """One changed file payload provided by CLI for review context."""

    model_config = ConfigDict(extra='forbid')

    path: str
    content: str


class ReviewRequest(BaseModel):
    """Request model for the /task/review endpoint."""

    model_config = ConfigDict(extra='forbid')

    run_id: str
    task_id: str | None = None
    iteration: int = Field(ge=1)
    prompt: str
    constitution: str
    reviewer_model: str = 'gpt-4.1-mini'
    execution_plan: ExecutionPlan
    final_diff: str
    changed_files: list[ChangedFile] = Field(default_factory=list)
    # Transitional fallback for callers that still send preformatted context.
    # Remove when every CLI caller sends structured changed_files.
    changed_file_contents: str | None = None

    @model_validator(mode='after')
    def validate_changed_inputs(self):
        """Require at least one source of changed file context."""
        has_changed_files = len(self.changed_files) > 0
        has_raw_contents = bool(self.changed_file_contents)

        if not has_changed_files and not has_raw_contents:
            raise ValueError(
                'Provide changed_files or changed_file_contents for review.'
            )

        return self


class ReviewResponse(BaseModel):
    """Response model for the /task/review endpoint."""

    ok: bool
    run_id: str
    task_id: str | None = None
    iteration: int
    approved: bool
    reviewer_feedback: str
    reviewers: list[ReviewerResult]
    reviewers_metrics: list[ReviewerMetrics]


__all__ = [
    'ChangedFile',
    'PlanRequest',
    'PlanResponse',
    'ReviewRequest',
    'ReviewResponse',
    'RunRequest',
    'RunResponse',
]
