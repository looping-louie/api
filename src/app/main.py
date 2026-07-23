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

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.bootstrap import configure_application
from src.app.routers import api_v1_router, router
from src.app.middleware import DevelopmentAuthMiddleware
from src.app.services.app_settings_service import get_app_settings
from src.app.utils.http import register_exception_handlers


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """Configure application dependencies during API startup."""

    await configure_application(app)
    yield

app = FastAPI(
    title="Looping Louie",
    description="Harness-as-a-Service runtime for iterative LLM development.",
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

settings = get_app_settings()

if settings.dev_auth_enabled:
    app.add_middleware(
        DevelopmentAuthMiddleware,
        user_id=settings.dev_user_id,
    )

app.include_router(api_v1_router)
app.include_router(router)
