"""Regression tests for retired public API routes."""

from fastapi import FastAPI

from src.app.routers import router


def test_deprecated_meeting_route_is_not_exposed() -> None:
    app = FastAPI()
    app.include_router(router)

    assert "/meeting/run" not in app.openapi()["paths"]
    assert "/meeting/run" not in {
        route.path for route in app.routes if hasattr(route, "path")
    }
