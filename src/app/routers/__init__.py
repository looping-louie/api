from fastapi import APIRouter
from src.app.schemas import RunHarnessRequest, RunResponse
from src.app.harness_runner import run_harness
from src.app.task_runner import RunTasksRequest, run_tasks


# Create the router instance
router = APIRouter()


@router.post("/run-harness", response_model=RunResponse)
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
