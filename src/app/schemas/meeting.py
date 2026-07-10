"""Meeting request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from src.app.schemas import RunMetrics


MeetingType = Literal['shape_idea', 'plan_implementation']


class RunRequest(BaseModel):
    """
    Input for one structured multi-persona meeting.

    The meeting planner selects participants, challengers, personas, and skills
    unless explicit constraints are supplied by the caller.
    """

    prompt: str
    meeting_type: MeetingType
    max_iterations: int = Field(default=3, ge=1, le=10)

    participant_model: str = 'deepseek-ai/DeepSeek-V4-Pro'
    challenger_model: str = 'gpt-4.1-mini'
    synthesizer_model: str = 'gpt-4.1-mini'
    planner_model: str = 'gpt-4.1-mini'

    required_personas: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    constitution: str = ''


class RunResponse(BaseModel):
    """
    Final response returned by the structured meeting endpoint.

    Contains the final generated artifact, approval state, complete meeting
    trace, and aggregated execution metrics.
    """

    run_id: str
    meeting_type: MeetingType
    final_output: str
    approved: bool
    run_metrics: RunMetrics
    execution_trace: list[dict]


__all__ = ['MeetingType', 'RunRequest', 'RunResponse']
