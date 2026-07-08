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


class GeneratorAssignment(BaseModel):
    """
    Generator configuration selected for one task.

    The persona determines how the generator approaches the work. Skills add
    task-specific technical knowledge, and focus narrows the assignment.
    """

    persona: str
    skills: list[str]
    focus: str


class ReviewerAssignment(BaseModel):
    """
    Reviewer configuration selected for one task.

    One reviewer combines a persona with one or more technical skills.
    """

    persona: str
    skills: list[str]
    strictness: int = Field(ge=0, le=100)
    focus: str


class ExecutionPlan(BaseModel):
    """
    Complete generator and reviewer strategy for one development task.
    """

    phase: ProjectPhase
    reasoning: str
    generator: GeneratorAssignment
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

    An execution plan is normally supplied by the execution planner. The
    static persona and skill fields remain available for direct calls to the
    harness when no planner is used.
    """

    prompt: str
    repo_path: str
    max_iterations: int = 3
    generator_model: str = "deepseek-ai/DeepSeek-V4-Pro"
    reviewer_model: str = "gpt-4.1-mini"

    generator_persona: str = "tech_lead"
    generator_skills: list[str] = Field(default_factory=list)
    reviewer_persona: str = "tech_lead"
    reviewer_skills: list[str] = Field(
        default_factory=lambda: ["small_patch_quality"]
    )

    execution_plan: ExecutionPlan | None = None
    constitution: str = ""


# TODO:
# Allow individual tasks to override execution settings such as
# models, skills and max_iterations.
class RunTasksRequest(BaseModel):
    """
    Request model for the /run-tasks endpoint.

    The execution planner selects the complete team for every task. Callers may
    force reviewer skills and may optionally fix the generator persona while
    leaving reviewer personas under planner control.
    """

    repo_path: str
    tasks_path: str
    max_iterations: int = 3
    generator_model: str = "deepseek-ai/DeepSeek-V4-Pro"
    reviewer_model: str = "gpt-4.1-mini"
    planner_model: str = "gpt-4.1-mini"
    required_reviewer_skills: list[str] = Field(default_factory=list)
    generator_persona: str | None = None


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

    Records the persona and skills that produced the measurements.
    """

    persona: str
    skills: list[str]


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

    persona: str
    skills: list[str]
    focus: str
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
