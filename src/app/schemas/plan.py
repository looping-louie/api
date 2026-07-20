"""Plan-related schemas."""

from typing import Literal

from pydantic import BaseModel

from src.app.schemas.generator import GeneratorAssignment
from src.app.schemas.reviewer import ReviewerAssignment


ProjectPhase = Literal['prototype', 'mvp', 'production']


class ExecutionPlan(BaseModel):
    """
    Complete generator and reviewer strategy for one development task.
    """

    phase: ProjectPhase
    reasoning: str
    generator: GeneratorAssignment
    reviewers: list[ReviewerAssignment]


__all__ = ['ProjectPhase', 'ExecutionPlan']
