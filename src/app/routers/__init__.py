from fastapi import APIRouter
from src.app.schemas import (
    GetTaskResponse,
    RunMeetingRequest,
    RunMeetingResponse,
    TaskContinueRequest,
    TaskContinueResponse,
    TaskStartRequest,
    TaskStartResponse,
)
from src.app.controllers.meeting import run_meeting
from src.app.controllers.task import continue_task, get_task, start_task


# Create the router instance
router = APIRouter()


@router.post("/meeting/run", response_model=RunMeetingResponse)
async def meeting_run_endpoint(
    req: RunMeetingRequest,
) -> RunMeetingResponse:
    """
    Execute one structured multi-persona meeting.

    Participants contribute proposals, challengers identify blocking issues,
    and the loop iterates until approval or the maximum number of rounds is
    reached.

    Returns the final generated artifact together with the complete meeting
    trace and execution metrics.
    """
    return await run_meeting(req)


@router.post('/task/start', response_model=TaskStartResponse)
async def task_start_endpoint(req: TaskStartRequest) -> TaskStartResponse:
    """Start checkpoint-based task execution and return first action."""
    return await start_task(req)


@router.post('/task/continue', response_model=TaskContinueResponse)
async def task_continue_endpoint(req: TaskContinueRequest) -> TaskContinueResponse:
    """Advance one checkpoint transition for an existing task run."""
    return await continue_task(req)


@router.get('/task/{run_id}', response_model=GetTaskResponse)
async def task_get_endpoint(run_id: str) -> GetTaskResponse:
    """Return latest checkpoint state for one task run identifier."""
    return await get_task(run_id)
