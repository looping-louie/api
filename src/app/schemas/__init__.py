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

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """
    Input for a single harness execution.
    """
    prompt: str
    repo_path: str
    max_iterations: int = 3
    generator_model: str = "deepseek-ai/DeepSeek-V4-Pro"
    reviewer_model: str = "gpt-4.1-mini"
    skills: list[str] = Field(default_factory=lambda: ["small_patch_quality"])


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
    skills: list[str] = Field(default_factory=lambda: ["small_patch_quality"])


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


class ReviewerResult(BaseModel):
    """
    Result returned by one reviewer skill.
    """
    skill: str
    approved: bool
    feedback: str
    metrics: ReviewerMetrics


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


class RunResponse(BaseModel):
    """
    Final response returned by the /run endpoint.

    Contains the final diff, approval status, execution trace
    and aggregated execution metrics.
    """
    run_id: str
    final_output: str
    approved: bool
    run_metrics: RunMetrics
    execution_trace: list[IterationTrace]
