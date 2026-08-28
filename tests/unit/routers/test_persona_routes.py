"""HTTP contract tests for persona routes."""

from collections.abc import Awaitable, Callable
from dataclasses import replace

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.personas import PersonaController
from src.app.routers.personas import router as personas_router
from src.app.services.persona_skills import (
    PersonaDefinitionService,
    SkillDefinitionService,
)
from src.app.utils.http import register_exception_handlers
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.unit.services.instructions.test_service import seed_builtin
from tests.unit.services.personas.test_service import build_persona_service


def build_app(*, controller: PersonaController) -> FastAPI:
    """Build an authenticated minimal application for persona route tests."""

    app = FastAPI()
    app.state.persona_controller = controller

    @app.middleware("http")
    async def add_authenticated_user(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Inject the authenticated user required by route dependencies."""

        request.state.user_id = "user-1"
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(personas_router, prefix="/api/v1")
    return app


@pytest.fixture
def persona_controller(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
) -> PersonaController:
    """Build a controller backed by deterministic in-memory fakes."""

    return PersonaController(
        persona_service=build_persona_service(
            persona_definition_service,
            skill_definition_service,
        ),
    )


def test_persona_rest_crud_routes(
    persona_controller: PersonaController,
) -> None:
    """Create, list, get, patch, and delete use the REST resource paths."""

    client = TestClient(build_app(controller=persona_controller))
    created = client.post(
        "/api/v1/personas",
        json={
            "name": "API_Reviewer",
            "description": "Reviews API contracts.",
            "instructions": "Review every public API contract.",
            "metadata": {"team": "platform"},
        },
    )

    assert created.status_code == 201
    persona_id = created.json()["id"]

    listed = client.get("/api/v1/personas")
    described = client.get(f"/api/v1/personas/{persona_id}")
    patched = client.patch(
        f"/api/v1/personas/{persona_id}",
        json={
            "expected_version": 1,
            "description": "Reviews REST API contracts.",
            "enabled": False,
        },
    )
    deleted = client.delete(f"/api/v1/personas/{persona_id}")

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert described.status_code == 200
    assert 'linked_service' not in described.json()
    assert 'config' not in described.json()
    assert described.json()["instructions"] == (
        "Review every public API contract."
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "Reviews REST API contracts."
    assert patched.json()["enabled"] is False
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}


def test_persona_routes_ignore_workspace_selection_header(
    persona_controller: PersonaController,
) -> None:
    """Persona routes use user scope even when a workspace header is supplied."""

    client = TestClient(build_app(controller=persona_controller))
    response = client.post(
        '/api/v1/personas',
        headers={'X-Project-ID': 'unrelated-workspace'},
        json={
            'name': 'User_scoped_persona',
            'instructions': 'Use user scope only.',
        },
    )

    assert response.status_code == 201


def test_create_persona_rejects_source_identifier(
    persona_controller: PersonaController,
) -> None:
    """POST accepts complete creation content rather than source identifiers."""

    client = TestClient(build_app(controller=persona_controller))

    response = client.post(
        "/api/v1/personas",
        json={
            "source_persona_id": "builtin:persona:source",
            "name": "Copied persona",
            "instructions": "Review the source.",
        },
    )

    assert response.status_code == 422


def test_persona_routes_create_and_replace_skill_associations(
    persona_controller: PersonaController,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """POST and PATCH expose explicit ordered persona skill IDs."""

    first_skill = seed_builtin(
        instruction_repository,
        instruction_type="skill",
    )
    second_skill = replace(
        first_skill,
        id="builtin:skill:privacy",
        name="Privacy",
    )
    instruction_repository.seed_available(second_skill)
    client = TestClient(build_app(controller=persona_controller))

    created = client.post(
        "/api/v1/personas",
        json={
            "name": "Platform_reviewer",
            "instructions": "Review platform changes.",
            "skill_ids": [first_skill.id, second_skill.id],
        },
    )
    persona_id = created.json()["id"]
    patched = client.patch(
        f"/api/v1/personas/{persona_id}",
        json={
            "expected_version": 1,
            "skill_ids": [second_skill.id],
        },
    )

    assert created.status_code == 201
    assert created.json()["skill_ids"] == [
        first_skill.id,
        second_skill.id,
    ]
    assert patched.status_code == 200
    assert patched.json()["skill_ids"] == [second_skill.id]


def test_persona_routes_reject_linked_service_selection(
    persona_controller: PersonaController,
) -> None:
    """POST no longer accepts execution routing fields on Personas."""

    client = TestClient(build_app(controller=persona_controller))
    response = client.post(
        '/api/v1/personas',
        json={
            'name': 'Service_reviewer',
            'instructions': 'Review service-backed work.',
            'linked_service': {
                'type': 'LinkedServiceReference',
                'reference_id': 'linked-service-1',
            },
            'config': {'model': 'service-model'},
        },
    )

    assert response.status_code == 422


def test_patch_changes_builtin_enabled_state_without_version(
    persona_controller: PersonaController,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """PATCH accepts a strict enabled value without expected_version."""

    builtin = seed_builtin(
        instruction_repository,
        instruction_type="persona",
    )
    client = TestClient(build_app(controller=persona_controller))

    disabled = client.patch(
        f"/api/v1/personas/{builtin.id}",
        json={"enabled": False},
    )
    enabled = client.patch(
        f"/api/v1/personas/{builtin.id}",
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
            "expected_version": 1,
            "skill_ids": ["skill-1", "skill-1"],
        },
        {
            'expected_version': 1,
            'linked_service': {
                'type': 'LinkedServiceReference',
                'reference_id': 'linked-service-1',
            },
        },
        {
            "expected_version": 1,
            "metadata": {"category": "unsupported"},
        },
    ],
)
def test_persona_write_payload_validation(
    persona_controller: PersonaController,
    payload: dict[str, object],
) -> None:
    """Write schemas reject empty, nullable, and ambiguous operations."""

    client = TestClient(build_app(controller=persona_controller))
    path = "/api/v1/personas/persona-1"
    response = client.patch(path, json=payload)

    assert response.status_code == 422


def test_direct_creation_requires_name_and_instructions(
    persona_controller: PersonaController,
) -> None:
    """POST rejects a direct creation without its required content."""

    client = TestClient(build_app(controller=persona_controller))

    response = client.post("/api/v1/personas", json={})

    assert response.status_code == 422


def test_persona_rejects_invalid_names_on_create_and_patch(
    persona_controller: PersonaController,
) -> None:
    """Persona names reject spaces and forbidden symbols on every write path."""

    client = TestClient(build_app(controller=persona_controller))
    invalid_create = client.post(
        '/api/v1/personas',
        json={
            'name': 'Invalid persona',
            'instructions': 'Review the change.',
        },
    )
    invalid_patch = client.patch(
        '/api/v1/personas/persona-1',
        json={'expected_version': 1, 'name': 'Invalid/name'},
    )

    assert invalid_create.status_code == 422
    assert invalid_patch.status_code == 422


def test_only_new_persona_routes_are_published(
    persona_controller: PersonaController,
) -> None:
    """OpenAPI exposes only collection and item persona operations."""

    client = TestClient(build_app(controller=persona_controller))
    paths = {
        path: set(methods)
        for path, methods in client.get("/openapi.json").json()["paths"].items()
    }

    assert paths == {
        "/api/v1/personas": {"get", "post"},
        "/api/v1/personas/{persona_id}": {
            "get",
            "patch",
            "delete",
        },
    }


def test_persona_legacy_model_is_absent_from_openapi(
    persona_controller: PersonaController,
) -> None:
    """OpenAPI no longer exposes retired Persona model fields."""

    client = TestClient(build_app(controller=persona_controller))
    schemas = client.get('/openapi.json').json()['components']['schemas']

    for schema_name in (
        'PersonaCreateRequest',
        'PersonaPatchRequest',
        'PersonaSummaryResponse',
        'PersonaResponse',
    ):
        assert 'model' not in schemas[schema_name]['properties']
