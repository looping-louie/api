from fastapi import APIRouter
from src.app.schemas import (
    PlanTaskRequest,
    PlanTaskResponse,
    ReviewTaskRequest,
    ReviewTaskResponse,
    RunWorkflowRequest,
    RunWorkflowResponse,
    RunMeetingRequest,
    RunMeetingResponse,
    RunTaskRequest,
    RunTaskResponse,
)
from src.app.controllers.workflow import run_workflow
from src.app.controllers.meeting import run_meeting
from src.app.controllers.task import plan_task, review_task, run_task


# Create the router instance
router = APIRouter()


@router.post("/workflow/run", response_model=RunWorkflowResponse)
async def workflow_run_endpoint(req: RunWorkflowRequest) -> RunWorkflowResponse:
    """
    Execute every pending task from a tasks.json file.

    Tasks are processed sequentially.
    Each approved task is committed immediately.
    Execution stops at the first task that cannot be approved.
    """
    return await run_workflow(req)


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


@router.post('/task/run', response_model=RunTaskResponse)
async def task_run_endpoint(req: RunTaskRequest) -> RunTaskResponse:
    """
    Execute one task through planner, harness, and commit stages.

    This endpoint mirrors the workflow inner loop for a single task.
    Transitional note:
    Kept as the compatibility path while /task/plan and /task/review are
    adopted by CLI-based execution.
    """
    return await run_task(req)


@router.post('/task/plan', response_model=PlanTaskResponse)
async def task_plan_endpoint(req: PlanTaskRequest) -> PlanTaskResponse:
    """Build one task execution plan without running harness."""
    return await plan_task(req)


@router.post('/task/review', response_model=ReviewTaskResponse)
async def task_review_endpoint(req: ReviewTaskRequest) -> ReviewTaskResponse:
    """Run reviewers against one CLI-provided candidate artifact."""
    return await review_task(req)
