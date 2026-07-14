"""
Looping Louie HTTP API.

This module exposes the public FastAPI endpoints.

Endpoints
---------
POST /workflow/run
    Executes a sequence of tasks defined in a tasks.json file.
    Each approved task is committed before the next one starts.
POST /task/run
    Executes a single pending task.
    Uses the same planner-harness-commit flow as workflow.

The API layer is intentionally thin.
Business logic lives in services and concise controller modules.
"""

from fastapi import FastAPI
from src.app.routers import router


app = FastAPI(
    title="Looping Louie",
    description="Harness-as-a-Service runtime for iterative LLM development.",
    version="0.1.0",
)


app.include_router(router)
