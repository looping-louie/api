"""Harness request/result schemas."""

from pydantic import BaseModel, Field

from src.app.schemas import ExecutionPlan, IterationTrace, RunMetrics


class RunRequest(BaseModel):
    """
    Input for a single harness execution.

    An execution plan must be supplied by the caller.
    """

    prompt: str
    repo_path: str
    max_iterations: int = 3
    generator_model: str = 'deepseek-ai/DeepSeek-V4-Pro'
    reviewer_model: str = 'gpt-4.1-mini'

    generator_persona: str = 'tech_lead'
    generator_skills: list[str] = Field(default_factory=list)
    reviewer_persona: str = 'tech_lead'
    reviewer_skills: list[str] = Field(
        default_factory=lambda: ['small_patch_quality']
    )

    execution_plan: ExecutionPlan
    constitution: str = ''


class RunResult(BaseModel):
    """
    Final response returned by one harness execution.

    Contains the final diff, approval status, execution trace
    and aggregated execution metrics.
    """

    run_id: str
    final_output: str
    approved: bool
    run_metrics: RunMetrics
    execution_trace: list[IterationTrace]


__all__ = ['RunRequest', 'RunResult']
