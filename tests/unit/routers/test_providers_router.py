"""HTTP contract tests for provider routes."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.provider import ProviderController
from src.app.routers.providers import router as providers_router
from src.app.services.providers.connection import (
    ProviderConnectionError,
)
from src.app.utils.http import register_exception_handlers
from tests.fakes.provider_connection_service import (
    FakeProviderConnectionService,
)


def build_app(
    *,
    controller: ProviderController,
    authenticated: bool = True,
) -> FastAPI:
    """Build a minimal provider API application."""

    app = FastAPI()
    app.state.provider_controller = controller

    if authenticated:

        @app.middleware("http")
        async def add_authenticated_user(
            request: Request,
            call_next: Callable[[Request], Awaitable[Response]],
        ) -> Response:
            """Inject the user expected by the request-context dependency."""

            request.state.user_id = "user-1"
            return await call_next(request)

    register_exception_handlers(app)
    app.include_router(providers_router, prefix="/api/v1")
    return app


def test_provider_collection_and_item_routes(
    provider_controller: ProviderController,
) -> None:
    """Collection and item GETs use the REST paths."""

    client = TestClient(build_app(controller=provider_controller))

    listed = client.get("/api/v1/providers")
    described = client.get("/api/v1/providers/ollama")

    assert listed.status_code == 200
    assert [item["provider"] for item in listed.json()] == [
        "anthropic",
        "nvidia",
        "ollama",
        "openai",
        "together",
    ]
    assert described.status_code == 200
    assert described.json()["provider"] == "ollama"


def test_patch_configures_provider_without_returning_secret(
    provider_controller: ProviderController,
) -> None:
    """PATCH stores configuration while keeping plaintext secrets private."""

    client = TestClient(build_app(controller=provider_controller))

    response = client.patch(
        "/api/v1/providers/openai",
        json={"api_key": "sk-test-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["enabled"] is True
    assert body["key_trimmed"] == "sk-te***************"
    assert "sk-test-secret" not in response.text
    assert "key_ciphertext" not in body


def test_patch_changes_enabled_state(
    provider_controller: ProviderController,
) -> None:
    """PATCH disables and re-enables an existing configuration."""

    client = TestClient(build_app(controller=provider_controller))
    configured = client.patch(
        "/api/v1/providers/openai",
        json={"api_key": "sk-test-secret"},
    )

    disabled = client.patch(
        "/api/v1/providers/openai",
        json={"enabled": False},
    )
    enabled = client.patch(
        "/api/v1/providers/openai",
        json={"enabled": True},
    )

    assert configured.status_code == 200
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True


def test_delete_removes_only_workspace_configuration(
    provider_controller: ProviderController,
) -> None:
    """DELETE resets workspace state while retaining the catalog provider."""

    client = TestClient(build_app(controller=provider_controller))
    client.patch(
        "/api/v1/providers/openai",
        json={"api_key": "sk-test-secret"},
    )

    deleted = client.delete("/api/v1/providers/openai")
    described = client.get("/api/v1/providers/openai")

    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}
    assert described.status_code == 200
    assert described.json()["configured"] is False


def test_unknown_provider_returns_404(
    provider_controller: ProviderController,
) -> None:
    """Catalog validation rejects unknown provider identifiers."""

    client = TestClient(build_app(controller=provider_controller))

    response = client.get("/api/v1/providers/unknown")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "provider_not_found"


def test_empty_patch_returns_422(
    provider_controller: ProviderController,
) -> None:
    """PATCH requires at least one explicitly supplied field."""

    client = TestClient(build_app(controller=provider_controller))

    response = client.patch("/api/v1/providers/openai", json={})

    assert response.status_code == 422


def test_patch_rejects_null_enabled(
    provider_controller: ProviderController,
) -> None:
    """The enabled field accepts only explicit boolean values."""

    client = TestClient(build_app(controller=provider_controller))

    response = client.patch(
        "/api/v1/providers/openai",
        json={"enabled": None},
    )

    assert response.status_code == 422


def test_connection_failure_does_not_configure_provider(
    provider_controller: ProviderController,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    """Connection errors retain the established gateway error contract."""

    provider_connection_service.error = ProviderConnectionError(
        "Connection failed."
    )
    client = TestClient(build_app(controller=provider_controller))

    response = client.patch(
        "/api/v1/providers/openai",
        json={"api_key": "sk-test-secret"},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "provider_connection_error"
    described = client.get("/api/v1/providers/openai")
    assert described.json()["configured"] is False


def test_only_new_provider_routes_are_published(
    provider_controller: ProviderController,
) -> None:
    """OpenAPI excludes all legacy provider action endpoints."""

    client = TestClient(build_app(controller=provider_controller))
    paths = {
        path: set(methods)
        for path, methods in client.get("/openapi.json").json()["paths"].items()
    }

    assert paths == {
        "/api/v1/providers": {"get"},
        "/api/v1/providers/{provider_id}": {
            "get",
            "patch",
            "delete",
        },
    }
    assert client.post("/api/v1/providers").status_code == 405


def test_provider_routes_require_authentication(
    provider_controller: ProviderController,
) -> None:
    """Provider routes reject requests without an authenticated user."""

    client = TestClient(
        build_app(
            controller=provider_controller,
            authenticated=False,
        )
    )

    response = client.get("/api/v1/providers")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"
