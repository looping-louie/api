"""Workflow-related API schemas."""

from pydantic import BaseModel, Field


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


__all__ = ['RunRequest']
