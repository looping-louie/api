"""Task request/response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.app.schemas.project import ProjectProfile
from src.app.schemas.workflow import CompletedTask, Task


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

    completed: CompletedTask | None = None
    task_id: str | None = None
    run_id: str | None = None
    approved: bool | None = None
    message: str | None = None


__all__ = ['RunRequest', 'RunResponse']
