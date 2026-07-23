"""Private helper functions for meeting controller."""

from pathlib import Path
from typing import Any

from src.app.schemas import RunMeetingRequest
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibrary,
)
from src.app.services.meeting.rounds import MeetingRoundResult
from src.app.services.meeting.runtime import UsageTotals
from src.app.services.meeting.team import MeetingPlan


async def execute_meeting_iterations(
    *,
    req: RunMeetingRequest,
    plan: MeetingPlan,
    usage: UsageTotals,
    run_path: Path,
    execute_meeting_round_fn: Any,
    instruction_library: ExecutionInstructionLibrary,
) -> tuple[list[dict[str, Any]], str, bool]:
    """Execute meeting rounds until approval or iteration limit."""
    trace: list[dict[str, Any]] = []
    current_artifact = ''
    previous_feedback = ''
    disagreements: list[str] = []
    approved = False

    for round_number in range(1, req.max_iterations + 1):
        result: MeetingRoundResult = await execute_meeting_round_fn(
            req=req,
            plan=plan,
            round_number=round_number,
            current_artifact=current_artifact,
            previous_feedback=previous_feedback,
            disagreements=disagreements,
            usage=usage,
            run_path=run_path,
            instruction_library=instruction_library,
        )
        current_artifact = result.artifact
        previous_feedback = result.feedback
        disagreements = result.disagreements
        approved = result.approved
        trace.append(result.trace)

        if approved:
            break

    return trace, current_artifact, approved
