"""HTTP contract tests for skill routes."""

from collections.abc import Awaitable, Callable

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.skill import SkillController
from src.app.routers.skills import router as skills_router
from src.app.services.shared.instruction_service import InstructionService
from src.app.utils.http import register_exception_handlers
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.services.test_instruction_service import seed_builtin
from tests.services.test_skill_service import build_skill_service


def build_app(*, controller: SkillController) -> FastAPI:
    """Build an authenticated minimal application for skill route tests."""

    app = FastAPI()
    app.state.skill_controller = controller

    @app.middleware("http")
    async def add_authenticated_user(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Inject the authenticated user required by route dependencies."""

        request.state.user_id = "user-1"
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(skills_router, prefix="/api/v1")
    return app


@pytest.fixture
def skill_controller(
    instruction_service: InstructionService,
) -> SkillController:
    """Build a controller backed by deterministic in-memory fakes."""

    return SkillController(
        skill_service=build_skill_service(instruction_service),
    )


def test_skill_rest_crud_routes(
    skill_controller: SkillController,
) -> None:
    """Create, list, get, patch, and delete use the REST resource paths."""

    client = TestClient(build_app(controller=skill_controller))
    created = client.post(
        "/api/v1/skills",
        json={
            "name": "API Compatibility",
            "description": "Reviews API contracts.",
            "instructions": "Review every public API contract.",
            "metadata": {
                "applies_when": ["HTTP contracts change"],
                "default_strictness": {"production": 100},
            },
        },
    )

    assert created.status_code == 201
    skill_id = created.json()["id"]

    listed = client.get("/api/v1/skills")
    described = client.get(f"/api/v1/skills/{skill_id}")
    patched = client.patch(
        f"/api/v1/skills/{skill_id}",
        json={
            "expected_version": 1,
            "description": "Reviews REST API contracts.",
            "enabled": False,
        },
    )
    deleted = client.delete(f"/api/v1/skills/{skill_id}")

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert described.status_code == 200
    assert described.json()["metadata"]["applies_when"] == [
        "HTTP contracts change"
    ]
    assert patched.status_code == 200
    assert patched.json()["description"] == "Reviews REST API contracts."
    assert patched.json()["enabled"] is False
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}


def test_create_skill_from_source(
    skill_controller: SkillController,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """POST copies an available source and records its lineage."""

    builtin = seed_builtin(
        instruction_repository,
        instruction_type="skill",
    )
    client = TestClient(build_app(controller=skill_controller))

    response = client.post(
        "/api/v1/skills",
        json={"source_skill_id": builtin.id},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == f"{builtin.name} Copy"
    assert body["description"] == builtin.description
    assert body["instructions"] == builtin.instructions
    assert body["metadata"]["applies_when"] == builtin.metadata["applies_when"]
    assert body["metadata"]["default_strictness"] is None
    assert body["source_instruction_id"] == builtin.id


def test_patch_changes_builtin_enabled_state_without_version(
    skill_controller: SkillController,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """PATCH accepts a strict enabled value without expected_version."""

    builtin = seed_builtin(
        instruction_repository,
        instruction_type="skill",
    )
    client = TestClient(build_app(controller=skill_controller))

    disabled = client.patch(
        f"/api/v1/skills/{builtin.id}",
        json={"enabled": False},
    )
    enabled = client.patch(
        f"/api/v1/skills/{builtin.id}",
        json={"enabled": True},
    )

    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"enabled": None},
        {"description": "Missing version"},
        {
            "source_skill_id": "builtin:skill:source",
            "instructions": "Do not override copied content.",
        },
    ],
)
def test_skill_write_payload_validation(
    skill_controller: SkillController,
    payload: dict[str, object],
) -> None:
    """Write schemas reject empty, nullable, and ambiguous operations."""

    client = TestClient(build_app(controller=skill_controller))
    path = "/api/v1/skills/skill-1"
    response = (
        client.post("/api/v1/skills", json=payload)
        if "source_skill_id" in payload
        else client.patch(path, json=payload)
    )

    assert response.status_code == 422


def test_direct_creation_requires_name_and_instructions(
    skill_controller: SkillController,
) -> None:
    """POST rejects a direct creation without its required content."""

    client = TestClient(build_app(controller=skill_controller))

    response = client.post("/api/v1/skills", json={})

    assert response.status_code == 422


def test_only_new_skill_routes_are_published(
    skill_controller: SkillController,
) -> None:
    """OpenAPI exposes only collection and item skill operations."""

    client = TestClient(build_app(controller=skill_controller))
    paths = {
        path: set(methods)
        for path, methods in client.get("/openapi.json").json()["paths"].items()
    }

    assert paths == {
        "/api/v1/skills": {"get", "post"},
        "/api/v1/skills/{skill_id}": {
            "get",
            "patch",
            "delete",
        },
    }


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/skills/list"),
        ("GET", "/api/v1/skills/describe/skill-1"),
        ("POST", "/api/v1/skills/create"),
        ("POST", "/api/v1/skills/update/skill-1"),
        ("PUT", "/api/v1/skills/skill-1/enabled"),
        ("POST", "/api/v1/skills/skill-1/duplicate"),
        ("DELETE", "/api/v1/skills/delete/skill-1"),
    ],
)
def test_legacy_skill_routes_are_unavailable(
    skill_controller: SkillController,
    method: str,
    path: str,
) -> None:
    """Legacy skill action paths no longer expose successful operations."""

    client = TestClient(build_app(controller=skill_controller))

    response = client.request(method, path)

    assert response.status_code in {404, 405}
