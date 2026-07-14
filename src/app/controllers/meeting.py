"""Controller for structured multi-persona meetings."""

import time
from typing import Any

from src.app.schemas import RunMeetingRequest, RunMeetingResponse
from src.app.services.meeting.meeting_planner_service import create_meeting_plan
from src.app.services.meeting.meeting_round_service import (
    MeetingRoundResult,
    execute_meeting_round,
)
from src.app.services.meeting.meeting_runtime_service import (
    UsageTotals,
    build_meeting_response,
    create_meeting_run,
    persist_meeting_response,
)
from src.app.services.meeting.meeting_team_service import MeetingPlan


async def run_meeting(req: RunMeetingRequest) -> RunMeetingResponse:
    """Coordinate one meeting until approval or the configured round limit."""
    started_at = time.perf_counter()
    run_id, run_path = create_meeting_run(req)
    usage = UsageTotals()
    plan: MeetingPlan = await create_meeting_plan(
        req=req,
        usage=usage,
        run_path=run_path,
    )

    trace: list[dict[str, Any]] = []
    current_artifact = ""
    previous_feedback = ""
    disagreements: list[str] = []
    approved = False

    for round_number in range(1, req.max_iterations + 1):
        result: MeetingRoundResult = await execute_meeting_round(
            req=req,
            plan=plan,
            round_number=round_number,
            current_artifact=current_artifact,
            previous_feedback=previous_feedback,
            disagreements=disagreements,
            usage=usage,
            run_path=run_path,
        )
        current_artifact = result.artifact
        previous_feedback = result.feedback
        disagreements = result.disagreements
        approved = result.approved
        trace.append(result.trace)

        if approved:
            break

    response: RunMeetingResponse = build_meeting_response(
        req=req,
        run_id=run_id,
        final_output=current_artifact,
        approved=approved,
        trace=trace,
        usage=usage,
        started_at=started_at,
    )
    persist_meeting_response(
        req=req,
        run_path=run_path,
        response=response,
    )
    return response
