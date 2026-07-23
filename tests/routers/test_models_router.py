from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.model import ModelController
from src.app.routers.models import router as models_router
from src.app.services.model_service import ProviderConnectionState
from src.app.utils.http import register_exception_handlers
from src.app.catalogs.models import ProviderId
from tests.fakes.provider_state_repository import (
    FakeProviderStateRepository,
)


def build_app(
    *,
    controller: ModelController,
    authenticated: bool = True,
) -> FastAPI:
    """Build a minimal FastAPI application for router tests."""

    app = FastAPI()
    app.state.model_controller = controller

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
        models_router,
        prefix="/api/v1",
    )

    return app


def test_list_models_route(
    model_controller: ModelController,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    client = TestClient(
        build_app(
            controller=model_controller,
        )
    )

    response = client.get(
        "/api/v1/models/list",
        params={
            "provider_id": "together",
            "available": "true",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] > 0
    assert all(
        item["available"] is True
        for item in body["items"]
    )
    assert all(
        "together" in item["providers"]
        for item in body["items"]
    )


def test_describe_model_route(
    model_controller: ModelController,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    client = TestClient(
        build_app(
            controller=model_controller,
        )
    )

    response = client.get(
        "/api/v1/models/describe/kimi-k2.6",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == "kimi-k2.6"
    assert body["available"] is True
    assert body["availability"][0]["provider_id"] == "together"


def test_describe_missing_model_returns_404(
    model_controller: ModelController,
) -> None:
    client = TestClient(
        build_app(
            controller=model_controller,
        )
    )

    response = client.get(
        "/api/v1/models/describe/missing-model",
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_not_found"


def test_models_routes_require_authentication(
    model_controller: ModelController,
) -> None:
    client = TestClient(
        build_app(
            controller=model_controller,
            authenticated=False,
        )
    )

    response = client.get(
        "/api/v1/models/list",
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == (
        "authentication_required"
    )


def test_list_models_validates_query_enums(
    model_controller: ModelController,
) -> None:
    client = TestClient(
        build_app(
            controller=model_controller,
        )
    )

    response = client.get(
        "/api/v1/models/list",
        params={
            "provider_id": "unsupported-provider",
        },
    )

    assert response.status_code == 422
