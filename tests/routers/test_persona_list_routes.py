"""HTTP contract tests for persona catalog listing queries."""

import pytest
from fastapi.testclient import TestClient

from src.app.controllers.persona import PersonaController
from src.app.services.instructions import InstructionService
from tests.routers.test_persona_routes import build_app
from tests.services.test_persona_service import build_persona_service


@pytest.fixture
def persona_controller(
    instruction_service: InstructionService,
) -> PersonaController:
    """Build a controller backed by deterministic in-memory fakes."""

    return PersonaController(
        persona_service=build_persona_service(instruction_service),
    )


def test_list_personas_filters_sorts_and_paginates(
    persona_controller: PersonaController,
) -> None:
    """List queries combine business categories, status, sort, and offset."""

    client = TestClient(build_app(controller=persona_controller))
    categories = [
        "software_engineering",
        "growth_acquisition",
    ]

    for index in range(14):
        created = client.post(
            "/api/v1/personas",
            json={
                "name": f"Persona {index:02d}",
                "description": "Catalog query fixture.",
                "instructions": "Act as this persona.",
                "metadata": {
                    "category": categories[index % 2],
                },
            },
        )
        assert created.status_code == 201

    disabled = client.patch(
        "/api/v1/personas/instruction-2",
        json={"enabled": False},
    )
    assert disabled.status_code == 200

    first_page = client.get(
        "/api/v1/personas",
        params={"sort": "newest", "offset": "0"},
    )
    second_page = client.get(
        "/api/v1/personas",
        params={"sort": "newest", "offset": "12"},
    )
    filtered = client.get(
        "/api/v1/personas",
        params=[
            ("category", "growth_acquisition"),
            ("status", "disabled"),
        ],
    )

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 14
    assert len(first_page.json()["items"]) == 12
    assert first_page.json()["items"][0]["name"] == "Persona 13"
    assert second_page.status_code == 200
    assert second_page.json()["total"] == 14
    assert len(second_page.json()["items"]) == 2
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["category"] == (
        "growth_acquisition"
    )


def test_list_personas_rejects_unknown_query_values(
    persona_controller: PersonaController,
) -> None:
    """Unsupported categories, statuses, sorts, and offsets return 422."""

    client = TestClient(build_app(controller=persona_controller))

    for params in (
        {"category": "other"},
        {"status": "archived"},
        {"sort": "popular"},
        {"offset": "-1"},
    ):
        assert client.get(
            "/api/v1/personas",
            params=params,
        ).status_code == 422
