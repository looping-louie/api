"""REST routes for checkpoint-based task execution."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.app.controllers.task import continue_task, get_task, start_task
from src.app.schemas import (
    GetTaskResponse,
    TaskContinueRequest,
    TaskContinueResponse,
    TaskStartRequest,
    TaskStartResponse,
)
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibraryService,
)

from .dependencies import (
    RequestContext,
    get_execution_instruction_library_service,
    get_request_context,
)


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)

ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]
InstructionLibraryDependency = Annotated[
    ExecutionInstructionLibraryService,
    Depends(get_execution_instruction_library_service),
]


@router.post("/start", response_model=TaskStartResponse)
async def start_task_endpoint(
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


@router.post("/continue", response_model=TaskContinueResponse)
async def continue_task_endpoint(
    req: TaskContinueRequest,
) -> TaskContinueResponse:
    """Advance one checkpoint transition for an existing task run."""
    return await continue_task(req)


@router.get("/{run_id}", response_model=GetTaskResponse)
async def get_task_endpoint(run_id: str) -> GetTaskResponse:
    """Return latest checkpoint state for one task run identifier."""
    return await get_task(run_id)
