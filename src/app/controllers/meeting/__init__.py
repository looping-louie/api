"""Controller for structured multi-persona meetings."""

import time
from typing import Any

from src.app.schemas import RunMeetingRequest, RunMeetingResponse
from src.app.services.meeting.planner import create_meeting_plan
from src.app.services.meeting.rounds import (
    MeetingRoundResult,
    execute_meeting_round,
)
from src.app.services.meeting.runtime import (
    UsageTotals,
    build_meeting_response,
    create_meeting_run,
    persist_meeting_response,
)
from src.app.services.meeting.team import MeetingPlan
from .utils import execute_meeting_iterations


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

    trace: list[dict[str, Any]]
    current_artifact: str
    approved: bool
    trace, current_artifact, approved = await execute_meeting_iterations(
        req=req,
        plan=plan,
        usage=usage,
        run_path=run_path,
        execute_meeting_round_fn=execute_meeting_round,
    )

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


__all__ = ['run_meeting']
