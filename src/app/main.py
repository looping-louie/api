"""
Looping Louie HTTP API.

This module exposes the public FastAPI endpoints.

Endpoints
---------
POST /run
    Executes a single harness run against a repository.

POST /run-tasks
    Executes a sequence of tasks defined in a tasks.json file.
    Each approved task is committed before the next one starts.

The API layer is intentionally thin.
Business logic lives in runner.py and task_runner.py.
"""

from fastapi import FastAPI

from src.app.runner import run_harness
from src.app.schemas import RunRequest, RunResponse
from src.app.task_runner import RunTasksRequest, run_tasks

app = FastAPI(
    title="Looping Louie",
    description="Harness-as-a-Service runtime for iterative LLM development.",
    version="0.1.0",
)


@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest):
    """
    Execute a single harness run.

    The repository is evolved inside an isolated git worktree.
    If every reviewer approves, the final diff is applied to the
    original repository without creating a commit.
    """
    return await run_harness(req)


@app.post("/run-tasks")
async def run_tasks_endpoint(req: RunTasksRequest):
    """
    Execute every pending task from a tasks.json file.

    Tasks are processed sequentially.
    Each approved task is committed immediately.
    Execution stops at the first task that cannot be approved.
    """
    return await run_tasks(req)
