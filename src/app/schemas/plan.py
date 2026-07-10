"""Plan-related schemas."""

from typing import Literal

from pydantic import BaseModel

from src.app.schemas.generator import GeneratorAssignment
from src.app.schemas.metrics import ModelMetrics
from src.app.schemas.reviewer import (
    ReviewerAssignment,
    ReviewerMetrics,
    ReviewerResult,
)


ProjectPhase = Literal['prototype', 'mvp', 'production']


class ExecutionPlan(BaseModel):
    """
    Complete generator and reviewer strategy for one development task.
    """

    phase: ProjectPhase
    reasoning: str
    generator: GeneratorAssignment
    reviewers: list[ReviewerAssignment]


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


__all__ = ['ProjectPhase', 'ExecutionPlan', 'IterationTrace']
