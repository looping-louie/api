"""Controller for starting a single-task execution."""

import uuid

from src.app.schemas.task import StartRequest, StartResponse
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibrary,
)

from . import utils


async def start_task(
    req: StartRequest,
    *,
    instruction_library: ExecutionInstructionLibrary,
) -> StartResponse:
    """Start a checkpoint-based task run and return first action."""
    run_id = uuid.uuid4().hex[:12]
    task = req.task.model_dump()

    if task["status"] != "pending":
        return StartResponse(
            ok=False,
            run_id=run_id,
            iteration=0,
            status="stopped",
            next_action="none",
            continuation_token=None,
            token_revision=0,
            message="Task status must be pending to start stepped execution.",
            recoverable=False,
        )

    state = utils.TaskRunState(
        run_id=run_id,
        task_id=task["id"],
        task_prompt=task["prompt"],
        task_commit_message=task["commit_message"],
        constitution=req.constitution,
        project_profile=req.project_profile.model_dump(),
        generator_model=req.generator_model,
        reviewer_model=req.reviewer_model,
        planner_model=req.planner_model,
        required_reviewer_skills=list(req.required_reviewer_skills),
        generator_persona=req.generator_persona,
        instruction_library=instruction_library,
        max_iterations=req.max_iterations,
        continuation_token=utils.new_continuation_token(),
        message="Run started. Provide workspace snapshot for iteration 1.",
    )
    utils.TASK_RUNS[run_id] = state
    return StartResponse(**utils.checkpoint_payload(state))
