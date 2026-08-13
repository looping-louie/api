"""HTTP contract tests for model catalog routes."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.catalogs.providers import ProviderId
from src.app.controllers.model import ModelController
from src.app.routers.models import router as models_router
from src.app.services.models.availability import ProviderConnectionState
from src.app.utils.http import register_exception_handlers
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
    """List responses honor provider and effective availability filters."""

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
        "/api/v1/models",
        params={
            "provider_id": "together",
            "available": "true",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] > 0
    assert len(body["items"]) <= 24
    assert all("released_at" in item for item in body["items"])
    assert all(
        item["available"] is True
        for item in body["items"]
    )
    assert all(
        "together" in item["providers"]
        for item in body["items"]
    )


def test_list_models_filters_sorts_and_paginates(
    model_controller: ModelController,
) -> None:
    """The route composes repeated labs, date sorting, and fixed pages."""

    client = TestClient(build_app(controller=model_controller))

    first_page = client.get(
        "/api/v1/models",
        params=[
            ("include_deprecated", "true"),
            ("lab", "openai"),
            ("lab", "anthropic"),
            ("sort", "newest"),
            ("offset", "0"),
        ],
    )

    assert first_page.status_code == 200
    body = first_page.json()
    assert body["items"]
    assert all(
        item["vendor"] in {"OpenAI", "Anthropic"}
        for item in body["items"]
    )
    release_dates = [item["released_at"] for item in body["items"]]
    assert release_dates == sorted(release_dates, reverse=True)

    all_models = client.get(
        "/api/v1/models",
        params={"include_deprecated": "true", "offset": "0"},
    ).json()
    second_page = client.get(
        "/api/v1/models",
        params={"include_deprecated": "true", "offset": "24"},
    ).json()

    assert all_models["total"] == 25
    assert len(all_models["items"]) == 24
    assert len(second_page["items"]) == 1
    assert second_page["total"] == 25


def test_describe_model_route(
    model_controller: ModelController,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Describe exposes the selected model and workspace availability."""

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
        "/api/v1/models/kimi-k2.6",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == "kimi-k2.6"
    assert body["available"] is True
    assert body["availability"][0]["provider_id"] == "together"


def test_describe_missing_model_returns_404(
    model_controller: ModelController,
) -> None:
    """Unknown model identifiers produce the public not-found error."""

    client = TestClient(
        build_app(
            controller=model_controller,
        )
    )

    response = client.get(
        "/api/v1/models/missing-model",
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_not_found"


def test_models_routes_require_authentication(
    model_controller: ModelController,
) -> None:
    """Every model route rejects requests without an authenticated user."""

    client = TestClient(
        build_app(
            controller=model_controller,
            authenticated=False,
        )
    )

    response = client.get(
        "/api/v1/models",
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == (
        "authentication_required"
    )


def test_list_models_validates_query_values(
    model_controller: ModelController,
) -> None:
    """Invalid enum, range, and text filters are rejected before dispatch."""

    client = TestClient(
        build_app(
            controller=model_controller,
        )
    )

    invalid_queries = (
        {"provider_id": "unsupported-provider"},
        {"lab": "unsupported-lab"},
        {"status": "unsupported-status"},
        {"sort": "unsupported-sort"},
        {"offset": "-1"},
        {"search": ""},
    )

    for params in invalid_queries:
        response = client.get("/api/v1/models", params=params)

        assert response.status_code == 422, params
