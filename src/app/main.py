"""Looping Louie FastAPI application and lifespan configuration."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app.bootstrap import configure_application
from src.app.routers import api_v1_router
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
    description="Decision engine for checkpoint-based iterative LLM development.",
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
