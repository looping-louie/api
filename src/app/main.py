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
from src.app.routers import router


app = FastAPI(
    title="Looping Louie",
    description="Harness-as-a-Service runtime for iterative LLM development.",
    version="0.1.0",
)


app.include_router(router)
