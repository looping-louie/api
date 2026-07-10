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
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Looping Louie",
    description="Harness-as-a-Service runtime for iterative LLM development.",
    version="0.1.0",
)

# Enables UI to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
