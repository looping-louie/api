"""HTTP contract tests for skill routes."""

from collections.abc import Awaitable, Callable

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.skill import SkillController
from src.app.routers.skills import router as skills_router
from src.app.services.instructions import SkillDefinitionService
from src.app.utils.http import register_exception_handlers
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.unit.services.instructions.test_service import seed_builtin
from tests.unit.services.skills.test_service import build_skill_service


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
    skill_definition_service: SkillDefinitionService,
) -> SkillController:
    """Build a controller backed by deterministic in-memory fakes."""

    return SkillController(
        skill_service=build_skill_service(skill_definition_service),
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


def test_create_skill_rejects_source_identifier(
    skill_controller: SkillController,
) -> None:
    """POST accepts complete creation content rather than source identifiers."""

    client = TestClient(build_app(controller=skill_controller))

    response = client.post(
        "/api/v1/skills",
        json={
            "source_skill_id": "builtin:skill:source",
            "name": "Copied skill",
            "instructions": "Review the source.",
        },
    )

    assert response.status_code == 422


def test_list_skills_filters_sorts_and_paginates(
    skill_controller: SkillController,
) -> None:
    """List queries combine business categories, status, sort, and offset."""

    client = TestClient(build_app(controller=skill_controller))
    categories = [
        "software_engineering",
        "growth_acquisition",
    ]

    for index in range(14):
        created = client.post(
            "/api/v1/skills",
            json={
                "name": f"Skill {index:02d}",
                "description": "Catalog query fixture.",
                "instructions": "Apply the skill.",
                "metadata": {
                    "category": categories[index % 2],
                },
            },
        )
        assert created.status_code == 201

    disabled = client.patch(
        "/api/v1/skills/skill-2",
        json={"enabled": False},
    )
    assert disabled.status_code == 200

    first_page = client.get(
        "/api/v1/skills",
        params={"sort": "newest", "offset": "0"},
    )
    second_page = client.get(
        "/api/v1/skills",
        params={"sort": "newest", "offset": "12"},
    )
    filtered = client.get(
        "/api/v1/skills",
        params=[
            ("category", "growth_acquisition"),
            ("status", "disabled"),
        ],
    )

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 14
    assert len(first_page.json()["items"]) == 12
    assert first_page.json()["items"][0]["name"] == "Skill 13"
    assert second_page.status_code == 200
    assert second_page.json()["total"] == 14
    assert len(second_page.json()["items"]) == 2
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["category"] == (
        "growth_acquisition"
    )


def test_list_skills_rejects_unknown_query_values(
    skill_controller: SkillController,
) -> None:
    """Unsupported categories, statuses, sorts, and offsets return 422."""

    client = TestClient(build_app(controller=skill_controller))

    for params in (
        {"category": "other"},
        {"status": "archived"},
        {"sort": "popular"},
        {"offset": "-1"},
    ):
        assert client.get("/api/v1/skills", params=params).status_code == 422


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
    ],
)
def test_skill_write_payload_validation(
    skill_controller: SkillController,
    payload: dict[str, object],
) -> None:
    """Write schemas reject empty, nullable, and ambiguous operations."""

    client = TestClient(build_app(controller=skill_controller))
    path = "/api/v1/skills/skill-1"
    response = client.patch(path, json=payload)

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
