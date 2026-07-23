from typing import Annotated

from fastapi import APIRouter, Depends
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
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibraryService,
)
from .dependencies import (
    RequestContext,
    get_execution_instruction_library_service,
    get_request_context,
)
from .api_v1 import router as api_v1_router

__all__ = [
    "api_v1_router",
    "router",
]

# Create the router instance
router = APIRouter()

ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]
InstructionLibraryDependency = Annotated[
    ExecutionInstructionLibraryService,
    Depends(get_execution_instruction_library_service),
]


@router.post("/meeting/run", response_model=RunMeetingResponse)
async def meeting_run_endpoint(
    req: RunMeetingRequest,
    context: ContextDependency,
    instruction_library_service: InstructionLibraryDependency,
) -> RunMeetingResponse:
    """
    Execute one structured multi-persona meeting.

    Participants contribute proposals, challengers identify blocking issues,
    and the loop iterates until approval or the maximum number of rounds is
    reached.

    Returns the final generated artifact together with the complete meeting
    trace and execution metrics.
    """
    instruction_library = await instruction_library_service.load(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
    )
    return await run_meeting(
        req,
        instruction_library=instruction_library,
    )


@router.post('/task/start', response_model=TaskStartResponse)
async def task_start_endpoint(
    req: TaskStartRequest,
    context: ContextDependency,
    instruction_library_service: InstructionLibraryDependency,
) -> TaskStartResponse:
    """Start checkpoint-based task execution and return first action."""
    instruction_library = await instruction_library_service.load(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
    )
    return await start_task(
        req,
        instruction_library=instruction_library,
    )


@router.post('/task/continue', response_model=TaskContinueResponse)
async def task_continue_endpoint(req: TaskContinueRequest) -> TaskContinueResponse:
    """Advance one checkpoint transition for an existing task run."""
    return await continue_task(req)


@router.get('/task/{run_id}', response_model=GetTaskResponse)
async def task_get_endpoint(run_id: str) -> GetTaskResponse:
    """Return latest checkpoint state for one task run identifier."""
    return await get_task(run_id)
