"""Controllers for single-task execution."""

from src.app.services.execution_planner import create_execution_plan
from src.app.services.llm_service.together import call_together
from src.app.schemas.task import ContinueRequest, ContinueResponse

from .continue_task import continue_task as _continue_task
from .get import get_task
from .start import start_task
from .utils import TASK_RUNS as _TASK_RUNS


async def continue_task(req: ContinueRequest) -> ContinueResponse:
    """Advance a task using the package-level injectable collaborators."""
    return await _continue_task(
        req,
        create_execution_plan_fn=create_execution_plan,
        call_together_fn=call_together,
    )

__all__ = ["continue_task", "get_task", "start_task"]
