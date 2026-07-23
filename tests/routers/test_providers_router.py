"""HTTP tests for provider RPC routes."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.provider import ProviderController
from src.app.routers.providers import router as providers_router
from src.app.services.providers.provider_connection_service import (
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
            request.state.user_id = "user-1"
            return await call_next(request)

    register_exception_handlers(app)
    app.include_router(
        providers_router,
        prefix="/api/v1",
    )

    return app


def test_list_providers_route(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    response = client.get(
        "/api/v1/providers/list",
    )

    assert response.status_code == 200

    body = response.json()

    assert [
        provider["provider"]
        for provider in body
    ] == [
        "anthropic",
        "nvidia",
        "ollama",
        "openai",
        "together",
    ]


def test_describe_provider_route(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    response = client.get(
        "/api/v1/providers/describe/ollama",
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "ollama"
    assert response.json()["requires_api_key"] is False


def test_configure_provider_route_never_returns_secret(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    response = client.post(
        "/api/v1/providers/configure/openai",
        json={
            "api_key": "sk-test-secret",
            "base_url": None,
        },
    )

    assert response.status_code == 200

    body = response.json()
    serialized = response.text

    assert body["provider"] == "openai"
    assert body["configured"] is True
    assert body["enabled"] is True
    assert body["key_trimmed"] == "sk-te***************"
    assert "sk-test-secret" not in serialized
    assert "key_ciphertext" not in body


def test_disable_and_enable_provider_routes(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    configured = client.post(
        "/api/v1/providers/configure/openai",
        json={
            "api_key": "sk-test-secret",
        },
    )

    assert configured.status_code == 200

    disabled = client.post(
        "/api/v1/providers/disable/openai",
    )

    assert disabled.status_code == 200
    assert disabled.json()["configured"] is True
    assert disabled.json()["enabled"] is False

    enabled = client.post(
        "/api/v1/providers/enable/openai",
    )

    assert enabled.status_code == 200
    assert enabled.json()["configured"] is True
    assert enabled.json()["enabled"] is True


def test_provider_connection_test_route(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    configured = client.post(
        "/api/v1/providers/configure/openai",
        json={
            "api_key": "sk-test-secret",
        },
    )

    assert configured.status_code == 200

    response = client.post(
        "/api/v1/providers/test/openai",
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "openai"
    assert response.json()["success"] is True


def test_delete_provider_route(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    configured = client.post(
        "/api/v1/providers/configure/openai",
        json={
            "api_key": "sk-test-secret",
        },
    )

    assert configured.status_code == 200

    deleted = client.delete(
        "/api/v1/providers/delete/openai",
    )

    assert deleted.status_code == 200
    assert deleted.json() == {
        "deleted": True,
    }

    described = client.get(
        "/api/v1/providers/describe/openai",
    )

    assert described.status_code == 200
    assert described.json()["configured"] is False


def test_unknown_provider_returns_404(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    response = client.get(
        "/api/v1/providers/describe/unknown",
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "provider_not_found"


def test_unconfigured_provider_test_returns_409(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    response = client.post(
        "/api/v1/providers/test/openai",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "provider_not_configured"
    )


def test_connection_failure_returns_502(
    provider_controller: ProviderController,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    provider_connection_service.error = ProviderConnectionError(
        "Connection failed."
    )
    client = TestClient(
        build_app(
            controller=provider_controller,
        )
    )

    response = client.post(
        "/api/v1/providers/configure/openai",
        json={
            "api_key": "sk-test-secret",
        },
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == (
        "provider_connection_error"
    )


def test_provider_routes_require_authentication(
    provider_controller: ProviderController,
) -> None:
    client = TestClient(
        build_app(
            controller=provider_controller,
            authenticated=False,
        )
    )

    response = client.get(
        "/api/v1/providers/list",
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == (
        "authentication_required"
    )
