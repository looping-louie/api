"""HTTP contract tests for task routes."""

from fastapi import FastAPI

from src.app.routers.tasks import router as tasks_router


def test_task_checkpoint_routes_use_versioned_resource_paths() -> None:
    app = FastAPI()
    app.include_router(tasks_router, prefix="/api/v1")
    paths = app.openapi()["paths"]

    assert set(paths) == {
        "/api/v1/tasks/start",
        "/api/v1/tasks/continue",
        "/api/v1/tasks/{run_id}",
    }
    assert set(paths["/api/v1/tasks/start"]) == {"post"}
    assert set(paths["/api/v1/tasks/continue"]) == {"post"}
    assert set(paths["/api/v1/tasks/{run_id}"]) == {"get"}
