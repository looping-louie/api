"""Workflow request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from src.app.schemas.generator import GeneratorAssignment
from src.app.schemas.plan import ProjectPhase
from src.app.schemas.reviewer import ReviewerAssignment


# TODO:
# Allow individual tasks to override execution settings such as
# models, skills and max_iterations.
class RunRequest(BaseModel):
    """
    Request model for the /workflow/run endpoint.

    The execution planner selects the complete team for every task. Callers may
    force reviewer skills and may optionally fix the generator persona while
    leaving reviewer personas under planner control.
    """

    repo_path: str
    tasks_path: str
    max_iterations: int = 3
    generator_model: str = 'deepseek-ai/DeepSeek-V4-Pro'
    reviewer_model: str = 'gpt-4.1-mini'
    planner_model: str = 'gpt-4.1-mini'
    required_reviewer_skills: list[str] = Field(default_factory=list)
    generator_persona: str | None = None


class CompletedTask(BaseModel):
    """One task completed during a workflow execution."""

    task_id: str
    run_id: str
    commit_sha: str
    commit_message: str
    phase: ProjectPhase
    reasoning: str
    generator: GeneratorAssignment
    reviewers: list[ReviewerAssignment]


class RunResponse(BaseModel):
    """Final response returned by the /workflow/run endpoint."""

    ok: bool
    status: Literal['completed', 'stopped']
    completed: list[CompletedTask]

    task_id: str | None = None
    run_id: str | None = None
    approved: bool | None = None
    message: str | None = None


__all__ = ['RunRequest', 'RunResponse']
