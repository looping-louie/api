from fastapi import APIRouter
from src.app.schemas import (
  RunTasksRequest,
  RunHarnessRequest,
  RunHarnessResponse,
  RunMeetingRequest,
  RunMeetingResponse
)
from src.app.controllers.harness_runner import run_harness
from src.app.controllers.tasks_runner import run_tasks
from src.app.controllers.meeting_runner import run_meeting


# Create the router instance
router = APIRouter()


@router.post("/run-harness", response_model=RunHarnessResponse)
async def run_harness_endpoint(req: RunHarnessRequest):
    """
    Execute a single harness run.

    The repository is evolved inside an isolated git worktree.
    If every reviewer approves, the final diff is applied to the
    original repository without creating a commit.
    """
    return await run_harness(req)


@router.post("/run-tasks")
async def run_tasks_endpoint(req: RunTasksRequest):
    """
    Execute every pending task from a tasks.json file.

    Tasks are processed sequentially.
    Each approved task is committed immediately.
    Execution stops at the first task that cannot be approved.
    """
    return await run_tasks(req)


@router.post("/run-meeting", response_model=RunMeetingResponse)
async def run_meeting_endpoint(
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
