"""HTTP contract tests for pipeline routes and validation errors."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.pipeline import PipelineController
from src.app.routers.pipelines import router as pipelines_router
from src.app.services.shared.tenant import TenantService
from src.app.utils.http import register_exception_handlers
from tests.services.test_pipeline_service import build_service


def build_client(*, tenant_service: TenantService) -> TestClient:
    """Build an authenticated pipeline application with in-memory storage."""

    service, _, _ = build_service(tenant_service=tenant_service)
    app = FastAPI()
    app.state.pipeline_controller = PipelineController(
        pipeline_service=service
    )

    @app.middleware("http")
    async def add_authenticated_user(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Inject the actor required by route dependencies."""

        request.state.user_id = "user-1"
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(pipelines_router, prefix="/api/v1")
    return TestClient(app)


def pipeline_payload(
    *,
    title: str = "Implementation pipeline",
    steps: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build one valid pipeline creation body."""

    return {
        "title": title,
        "description": "Implement and validate.",
        "steps": (
            steps
            if steps is not None
            else [
                {"type": "loop", "loop_id": "loop-1"},
                {"type": "human_gate", "gate_type": "approval"},
            ]
        ),
    }


def quiz(
    *,
    config: dict[str, object] | None,
) -> dict[str, object]:
    """Build one quiz gate body, optionally without configuration."""

    step: dict[str, object] = {
        "type": "human_gate",
        "gate_type": "quiz",
    }
    if config is not None:
        step["config"] = config
    return step


def test_pipeline_crud_changelog_and_archival_routes(
    tenant_service: TenantService,
) -> None:
    """Create, read, replace, audit, and archive use REST contracts."""

    client = build_client(tenant_service=tenant_service)
    created_response = client.post(
        "/api/v1/pipelines",
        json=pipeline_payload(),
    )
    assert created_response.status_code == 201
    created = created_response.json()
    pipeline_id = created["id"]
    assert created["enabled"] is True

    fetched = client.get(f"/api/v1/pipelines/{pipeline_id}")
    patched = client.patch(
        f"/api/v1/pipelines/{pipeline_id}",
        json={
            "steps": [
                {"type": "human_gate", "gate_type": "approval"},
                {"type": "loop", "loop_id": "loop-1"},
            ]
        },
    )
    changelog = client.get(
        f"/api/v1/pipelines/{pipeline_id}/changelog"
    )
    deleted = client.delete(f"/api/v1/pipelines/{pipeline_id}")
    listed = client.get("/api/v1/pipelines")
    archived = client.get("/api/v1/pipelines?status=archived")

    assert fetched.status_code == 200
    assert patched.json()["steps"][0]["type"] == "human_gate"
    assert changelog.json()["items"][0]["diff"]["steps"][
        "order_changes"
    ]
    assert deleted.json() == {"deleted": True}
    assert listed.json() == {"items": [], "total": 0}
    assert archived.json()["total"] == 1
    assert archived.json()["items"][0]["enabled"] is False
    conflict = client.patch(
        f"/api/v1/pipelines/{pipeline_id}",
        json={"enabled": True},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "pipeline_archived"


def test_quiz_defaults_and_configuration_preservation(
    tenant_service: TenantService,
) -> None:
    """Quiz request defaults are materialized and explicit values survive."""

    client = build_client(tenant_service=tenant_service)
    defaulted = client.post(
        "/api/v1/pipelines",
        json=pipeline_payload(
            steps=[
                {"type": "loop", "loop_id": "loop-1"},
                quiz(config={"minimum_correct_answers": 5}),
            ]
        ),
    )
    explicit = client.post(
        "/api/v1/pipelines",
        json=pipeline_payload(
            steps=[
                {"type": "loop", "loop_id": "loop-1"},
                quiz(
                    config={
                        "minimum_correct_answers": 8,
                        "question_count": 12,
                        "option_count": 4,
                    }
                ),
            ]
        ),
    )

    assert defaulted.status_code == 201
    assert defaulted.json()["steps"][1]["config"] == {
        "minimum_correct_answers": 5,
        "question_count": 10,
        "option_count": 3,
    }
    assert explicit.json()["steps"][1]["config"] == {
        "minimum_correct_answers": 8,
        "question_count": 12,
        "option_count": 4,
    }


def test_invalid_pipeline_steps_use_stable_error_envelope(
    tenant_service: TenantService,
) -> None:
    """Structural and numeric step failures map to invalid_pipeline_steps."""

    client = build_client(tenant_service=tenant_service)
    invalid_steps = [
        [],
        [{"type": "loop", "loop_id": "loop-1"}],
        [
            {"type": "loop", "loop_id": "loop-1"},
            quiz(config=None),
        ],
        [
            {"type": "loop", "loop_id": "loop-1"},
            quiz(config={"question_count": 10}),
        ],
        [
            {"type": "loop", "loop_id": "loop-1"},
            quiz(
                config={
                    "minimum_correct_answers": 11,
                    "question_count": 10,
                }
            ),
        ],
        [
            {"type": "loop", "loop_id": "loop-1"},
            quiz(config={"minimum_correct_answers": 0}),
        ],
        [
            {"type": "loop", "loop_id": "loop-1"},
            quiz(
                config={
                    "minimum_correct_answers": 1,
                    "option_count": 1,
                }
            ),
        ],
        [
            {"type": "loop", "loop_id": "loop-1"},
            {
                "type": "human_gate",
                "gate_type": "approval",
                "config": {"minimum_correct_answers": 1},
            },
        ],
        [
            {"type": "loop", "loop_id": "loop-1"},
            quiz(
                config={
                    "minimum_correct_answers": 1,
                    "questions": [],
                }
            ),
        ],
    ]

    for steps in invalid_steps:
        response = client.post(
            "/api/v1/pipelines",
            json=pipeline_payload(steps=steps),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_pipeline_steps"
        assert response.json()["error"]["details"]

    pipeline_id = client.post(
        "/api/v1/pipelines",
        json=pipeline_payload(),
    ).json()["id"]
    invalid_patch = client.patch(
        f"/api/v1/pipelines/{pipeline_id}",
        json={"steps": [{"type": "loop", "loop_id": "loop-1"}]},
    )
    assert invalid_patch.json()["error"]["code"] == "invalid_pipeline_steps"


def test_discriminator_and_reference_errors_use_stable_codes(
    tenant_service: TenantService,
) -> None:
    """Unknown discriminators and missing loops retain their exact codes."""

    client = build_client(tenant_service=tenant_service)
    cases = [
        (
            [
                {"type": "loop", "loop_id": "loop-1"},
                {"type": "branch"},
            ],
            "unsupported_pipeline_step",
        ),
        (
            [
                {"type": "loop", "loop_id": "loop-1"},
                {"type": "human_gate", "gate_type": "review"},
            ],
            "unsupported_human_gate_type",
        ),
        (
            [
                {"type": "loop", "loop_id": "missing"},
                {"type": "human_gate", "gate_type": "approval"},
            ],
            "loop_not_found",
        ),
    ]

    for steps, expected_code in cases:
        response = client.post(
            "/api/v1/pipelines",
            json=pipeline_payload(steps=steps),
        )
        assert response.status_code in {404, 422}
        assert response.json()["error"]["code"] == expected_code


def test_generic_body_validation_also_uses_api_envelope(
    tenant_service: TenantService,
) -> None:
    """Non-step request failures no longer return FastAPI's detail shape."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        "/api/v1/pipelines",
        json={"description": "Missing title.", "steps": []},
    )

    assert response.status_code == 422
    assert "error" in response.json() and "detail" not in response.json()
