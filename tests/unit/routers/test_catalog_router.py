"""HTTP contract tests for static catalog routes."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.catalog import CatalogController
from src.app.routers.catalog import router as catalog_router
from src.app.services.catalog import CatalogService
from src.app.utils.http import register_exception_handlers


def build_app(*, authenticated: bool = True) -> FastAPI:
    """Build a minimal application configured with static catalogs."""

    app = FastAPI()
    app.state.catalog_controller = CatalogController(
        catalog_service=CatalogService(),
    )

    if authenticated:

        @app.middleware('http')
        async def add_authenticated_user(
            request: Request,
            call_next: Callable[[Request], Awaitable[Response]],
        ) -> Response:
            """Inject the authenticated user required by route dependencies."""

            request.state.user_id = 'user-1'
            return await call_next(request)

    register_exception_handlers(app)
    app.include_router(catalog_router, prefix='/api/v1')
    return app


def test_catalog_routes_return_only_static_metadata() -> None:
    """Catalog routes exclude all workspace configuration and availability."""

    client = TestClient(build_app())

    providers_response = client.get('/api/v1/catalog/providers')
    models_response = client.get('/api/v1/catalog/models')

    assert providers_response.status_code == 200
    provider = providers_response.json()[0]
    assert provider['id'] == 'anthropic'
    assert 'configured' not in provider
    assert 'enabled' not in provider
    assert 'key_trimmed' not in provider

    assert models_response.status_code == 200
    model = models_response.json()['items'][0]
    assert model['provider_ids']
    assert 'available' not in model
    assert 'availability' not in model


def test_catalog_routes_require_authentication() -> None:
    """Catalog reads remain protected API operations without workspace state."""

    client = TestClient(build_app(authenticated=False))

    response = client.get('/api/v1/catalog/providers')

    assert response.status_code == 401
    assert response.json()['detail']['code'] == 'authentication_required'