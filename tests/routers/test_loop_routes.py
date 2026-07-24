"""HTTP contract tests for loop routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.loop import LoopController
from src.app.routers.loops import router as loops_router
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant_service import TenantService
from src.app.utils.http import register_exception_handlers
from tests.fakes.loop_repository import FakeLoopRepository
from tests.fakes.reference_repository import FakeReferenceRepository
from tests.services.test_loop_service import build_service, seed_references


def build_app(*, controller: LoopController) -> FastAPI:
    """Build an authenticated minimal loop application."""

    app = FastAPI()
    app.state.loop_controller = controller

    @app.middleware("http")
    async def add_authenticated_user(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Inject the actor required by route dependencies."""

        request.state.user_id = "user-1"
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(loops_router, prefix="/api/v1")
    return app


def build_client(
    *,
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
    repository: FakeLoopRepository | None = None,
) -> TestClient:
    """Build a client backed by deterministic in-memory dependencies."""

    seed_references(reference_repository)
    service = build_service(
        repository=repository or FakeLoopRepository(),
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
    )
    return TestClient(
        build_app(controller=LoopController(loop_service=service))
    )


def direct_payload(*, title: str = "Direct loop") -> dict[str, object]:
    """Return one valid direct-flow request body."""

    return {
        "title": title,
        "description": "Produce one answer.",
        "flow": "direct",
        "stop_conditions": {"max_tokens": 5000},
        "agents": [
            {
                "model_id": "model-1",
                "persona_id": "persona-1",
                "role": "generator",
            }
        ],
        "output_contract": {
            "type": "text",
            "description": "Human-readable answer.",
        },
    }


def test_loop_rest_crud_and_changelog_routes(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Create, list, get, patch, audit, and delete use REST paths."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    created_response = client.post(
        "/api/v1/loops",
        json=direct_payload(),
    )
    assert created_response.status_code == 201
    created = created_response.json()
    loop_id = created["id"]
    assert created["status"] == "active"
    assert created["created_by"] == "user-1"
    assert created["agents"][0]["id"]
    assert "skill_ids" not in created["agents"][0]

    listed = client.get("/api/v1/loops?offset=0")
    fetched = client.get(f"/api/v1/loops/{loop_id}")
    patched = client.patch(
        f"/api/v1/loops/{loop_id}",
        json={"description": "Updated answer."},
    )
    changelog = client.get(
        f"/api/v1/loops/{loop_id}/changelog"
    )
    deleted = client.delete(f"/api/v1/loops/{loop_id}")
    retained = client.get(
        f"/api/v1/loops/{loop_id}/changelog"
    )

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert fetched.json()["title"] == "Direct loop"
    assert patched.json()["description"] == "Updated answer."
    assert changelog.json()["items"][0]["change_type"] == "updated"
    assert all(
        item["actor_id"] == "user-1"
        for item in changelog.json()["items"]
    )
    assert changelog.json()["items"][0]["diff"] == {
        "description": {
            "from": "Produce one answer.",
            "to": "Updated answer.",
        }
    }
    assert deleted.json() == {"deleted": True}
    assert retained.status_code == 200
    assert retained.json()["items"][0]["change_type"] == "deleted"
    assert retained.json()["items"][0]["actor_id"] == "user-1"
    assert client.get(f"/api/v1/loops/{loop_id}").status_code == 404


def test_loop_listing_uses_fixed_ten_item_pages(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Offset advances through a collection whose page size is always ten."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    for position in range(12):
        response = client.post(
            "/api/v1/loops",
            json=direct_payload(title=f"Loop {position:02d}"),
        )
        assert response.status_code == 201

    first = client.get("/api/v1/loops")
    second = client.get("/api/v1/loops?offset=10")

    assert first.json()["total"] == 12
    assert len(first.json()["items"]) == 10
    assert second.json()["total"] == 12
    assert len(second.json()["items"]) == 2


def test_loop_payload_rejects_skills_and_invalid_contracts(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Strict write schemas reject skills and incomplete fields."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    with_skills = direct_payload()
    with_skills["agents"][0]["skill_ids"] = ["skill-1"]
    invalid_json = direct_payload()
    invalid_json["output_contract"] = {
        "type": "json",
        "description": "JSON answer.",
    }
    invalid_files = direct_payload()
    invalid_files["output_contract"] = {
        "type": "files",
        "description": "File answer.",
    }
    missing_stops = direct_payload()
    missing_stops["stop_conditions"] = {}
    negative_stops = direct_payload()
    negative_stops["stop_conditions"] = {"max_iterations": -1}
    invalid_flow = direct_payload()
    invalid_flow["flow"] = "pipeline"
    invalid_role = direct_payload()
    invalid_role["agents"][0]["role"] = "chair"

    for payload in (
        with_skills,
        invalid_json,
        invalid_files,
        missing_stops,
        negative_stops,
        invalid_flow,
        invalid_role,
    ):
        assert client.post("/api/v1/loops", json=payload).status_code == 422


def test_patch_rejects_empty_noop_and_immutable_fields(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """PATCH accepts only effective mutable changes."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    loop_id = client.post(
        "/api/v1/loops",
        json=direct_payload(),
    ).json()["id"]

    assert client.patch(
        f"/api/v1/loops/{loop_id}", json={}
    ).status_code == 422
    assert client.patch(
        f"/api/v1/loops/{loop_id}",
        json={"title": "Direct loop"},
    ).status_code == 422
    assert client.patch(
        f"/api/v1/loops/{loop_id}",
        json={"created_by": "forged"},
    ).status_code == 422
    assert client.get(
        "/api/v1/loops/unknown/changelog"
    ).status_code == 404


def test_only_new_loop_routes_are_published(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """OpenAPI publishes only the new loop resource endpoints."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    paths = set(client.get("/openapi.json").json()["paths"])

    assert paths == {
        "/api/v1/loops",
        "/api/v1/loops/{loop_id}",
        "/api/v1/loops/{loop_id}/changelog",
    }
