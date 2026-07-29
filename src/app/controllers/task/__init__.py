"""Controllers for single-task execution."""

from src.app.schemas.task import ContinueRequest, ContinueResponse
from src.app.services.execution_planner import create_execution_plan
from src.app.services.llm_service.together import call_together

from .describe import describe_task
from .resume import resume_task as _resume_task
from .start import start_task
from .utils import TASK_RUNS as _TASK_RUNS


async def resume_task(req: ContinueRequest) -> ContinueResponse:
    """Advance a task using the package-level injectable collaborators."""
    return await _resume_task(
        req,
        create_execution_plan_fn=create_execution_plan,
        call_together_fn=call_together,
    )

__all__ = ["describe_task", "resume_task", "start_task"]
