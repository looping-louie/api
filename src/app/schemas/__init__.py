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


ProjectPhase = Literal['prototype', 'mvp', 'production']


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


# NOTE:
# These imports are intentionally placed at the bottom to avoid circular
# imports. Module-level request/response schemas depend on shared classes
# defined above (ExecutionPlan, IterationTrace, RunMetrics), so importing them
# earlier would initialize src.app.schemas before those classes exist.
# pylint: disable=wrong-import-position
from src.app.schemas.harness import (
    RunRequest as RunHarnessRequest,
    RunResponse as RunHarnessResponse,
)
from src.app.schemas.meeting import (
    MeetingType,
    RunRequest as RunMeetingRequest,
    RunResponse as RunMeetingResponse,
)
from src.app.schemas.tasks import RunRequest as RunTasksRequest


__all__ = [
    'ExecutionPlan',
    'GeneratorAssignment',
    'IterationTrace',
    'MeetingType',
    'ModelMetrics',
    'ProjectPhase',
    'ReviewerAssignment',
    'ReviewerIssue',
    'ReviewerMetrics',
    'ReviewerResult',
    'RunHarnessRequest',
    'RunHarnessResponse',
    'RunMeetingRequest',
    'RunMeetingResponse',
    'RunMetrics',
    'RunTasksRequest',
]
