"""
Public API schemas.

These models define the contract between the HTTP API and clients.

The runner internally exchanges richer Python objects, but every request
and response crossing the API boundary is validated through these schemas.

The hierarchy is intentionally split into:
- requests
- metrics
- reviewer results
- execution trace
- run response
"""

from typing import Literal
from pydantic import BaseModel, Field


ProjectPhase = Literal["prototype", "mvp", "production"]


class ReviewerAssignment(BaseModel):
    """
    One reviewer selected by the skill planner.
    """
    skill: str
    strictness: int = Field(ge=0, le=100)
    focus: str


class SkillPlan(BaseModel):
    """
    Review strategy selected for one development task.
    """
    phase: ProjectPhase
    reasoning: str
    reviewers: list[ReviewerAssignment]


class ReviewerIssue(BaseModel):
    """
    One concrete issue found by a reviewer.
    """
    title: str
    description: str
    file: str | None = None


class RunHarnessRequest(BaseModel):
    """
    Input for a single harness execution.
    """
    prompt: str
    repo_path: str
    max_iterations: int = 3
    generator_model: str = "deepseek-ai/DeepSeek-V4-Pro"
    reviewer_model: str = "gpt-4.1-mini"
    skills: list[str] = Field(default_factory=lambda: ["small_patch_quality"])
    skill_plan: SkillPlan | None = None
    constitution: str = ""

# TODO:
# Allow individual tasks to override execution settings such as
# models, skills and max_iterations.
class RunTasksRequest(BaseModel):
    """
    Request model for the /run-tasks endpoint.

    Defines the repository, task file and default execution parameters that
    will be used for every pending task unless future task-level overrides
    are introduced.
    """
    repo_path: str
    tasks_path: str
    max_iterations: int = 3
    generator_model: str = "deepseek-ai/DeepSeek-V4-Pro"
    reviewer_model: str = "gpt-4.1-mini"
    planner_model: str = "gpt-4.1-mini"
    skills: list[str] = Field(default_factory=list)


class ModelMetrics(BaseModel):
    """
    Performance metrics collected from one LLM invocation.

    These metrics are provider-agnostic so they can represent Together,
    OpenAI, Anthropic or future providers uniformly.
    """
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    duration_ms: int = 0
    tokens_per_second: float = 0


class ReviewerMetrics(ModelMetrics):
    """
    Metrics for one reviewer invocation.

    Extends ModelMetrics by recording which review skill produced
    the measurements.
    """
    skill: str


class RunMetrics(BaseModel):
    """
    Aggregated metrics for the complete harness execution.

    Includes generator and every reviewer across every iteration.
    """
    iterations: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    duration_ms: int
    tokens_per_second: float
    estimated_cost_eur: float = 0


class ReviewerResult(BaseModel):
    """
    Normalised reviewer result enriched by the harness.

    Execution metadata is generated locally and never trusted to the model.
    """
    skill: str
    model: str
    run_id: str
    iteration: int
    phase: ProjectPhase
    strictness: int

    score: int = Field(ge=0, le=100)
    blocking_issues: list[ReviewerIssue]
    feedback: str
    approved: bool

    metrics: ReviewerMetrics


# TODO:
# Split infrastructure failures from reviewer results.
# System errors (parser failures, git failures, provider failures)
# should become a first-class field instead of synthetic reviewers.
class IterationTrace(BaseModel):
    """
    Complete record of one harness iteration.

    Stores generator output, reviewer feedback, approval state
    and all metrics required to replay or inspect the iteration.
    """
    iteration: int
    generator_output: str
    reviewer_feedback: str
    approved: bool
    generator_metrics: ModelMetrics
    reviewers: list[ReviewerResult]
    reviewers_metrics: list[ReviewerMetrics]


class RunHarnessResponse(BaseModel):
    """
    Final response returned by the /run-harness endpoint.

    Contains the final diff, approval status, execution trace
    and aggregated execution metrics.
    """
    run_id: str
    final_output: str
    approved: bool
    run_metrics: RunMetrics
    execution_trace: list[IterationTrace]
