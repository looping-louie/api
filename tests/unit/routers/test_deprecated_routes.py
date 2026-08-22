"""Regression tests for retired public API routes."""

from fastapi import FastAPI

from src.app.routers import api_v1_router


def test_deprecated_meeting_route_is_not_exposed() -> None:
    app = FastAPI()
    app.include_router(api_v1_router)

    assert "/meeting/run" not in app.openapi()["paths"]
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/meeting/run" not in paths


def test_legacy_root_task_routes_are_not_exposed() -> None:
    app = FastAPI()
    app.include_router(api_v1_router)
    paths = set(app.openapi()["paths"])

    assert "/task/start" not in paths
    assert "/task/continue" not in paths
    assert "/task/{run_id}" not in paths


def test_legacy_loop_routes_are_not_exposed() -> None:
    """The Activity resource replaces public loop management routes."""

    app = FastAPI()
    app.include_router(api_v1_router)
    paths = set(app.openapi()['paths'])

    assert not any(path.startswith('/api/v1/loops') for path in paths)


def test_legacy_provider_routes_are_not_exposed() -> None:
    """Linked Services replaces public legacy Provider configuration routes."""

    app = FastAPI()
    app.include_router(api_v1_router)
    paths = set(app.openapi()['paths'])

    assert '/api/v1/providers' not in paths
    assert '/api/v1/providers/{provider_id}' not in paths
