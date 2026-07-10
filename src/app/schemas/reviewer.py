"""Reviewer-related schemas."""

from pydantic import BaseModel, Field

from src.app.schemas import ModelMetrics, ProjectPhase


class ReviewerAssignment(BaseModel):
    """
    Reviewer configuration selected for one task.

    One reviewer combines a persona with one or more technical skills.
    """

    persona: str
    skills: list[str]
    strictness: int = Field(ge=0, le=100)
    focus: str


class ReviewerIssue(BaseModel):
    """
    One concrete issue found by a reviewer.
    """

    title: str
    description: str
    file: str | None = None


class ReviewerMetrics(ModelMetrics):
    """
    Metrics for one reviewer invocation.

    Records the persona and skills that produced the measurements.
    """

    persona: str
    skills: list[str]


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


__all__ = [
    'ReviewerAssignment',
    'ReviewerIssue',
    'ReviewerMetrics',
    'ReviewerResult',
]
