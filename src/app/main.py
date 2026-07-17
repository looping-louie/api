"""
Looping Louie HTTP API.

This module exposes the public FastAPI endpoints.

Endpoints
---------
POST /task/start
    Starts one checkpoint-based task run.
POST /task/continue
    Advances one checkpoint transition for a run.
GET /task/{run_id}
    Returns the latest checkpoint state for one run.

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
