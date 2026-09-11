"""HTTP contract tests for static catalog routes."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.catalogs import CatalogController
from src.app.routers.catalog import router as catalog_router
from src.app.services.catalogs import StaticCatalogService
from src.app.utils.http import register_exception_handlers


def build_app(*, authenticated: bool = True) -> FastAPI:
    """Build a minimal application configured with static catalogs."""

    app = FastAPI()
    app.state.catalog_controller = CatalogController(
        static_catalog_service=StaticCatalogService(),
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
    personas_response = client.get('/api/v1/catalog/personas')
    skills_response = client.get('/api/v1/catalog/skills')

    assert providers_response.status_code == 200
    provider = providers_response.json()[0]
    assert provider['id'] == 'anthropic'
    assert provider['offerings']
    offering = provider['offerings'][0]
    assert {
        'model_id',
        'provider_model_id',
        'endpoint',
        'context_window',
        'max_output_tokens',
        'pricing',
        'status',
        'deprecated_at',
    } <= offering.keys()
    assert 'configured' not in provider
    assert 'enabled' not in provider
    assert 'key_trimmed' not in provider

    assert models_response.status_code == 200
    models = models_response.json()
    assert models['total'] == len(models['items'])
    model = models['items'][0]
    assert 'provider_ids' not in model
    assert 'deployment_count' not in model
    assert 'starting_price' not in model
    assert 'available' not in model
    assert 'availability' not in model

    assert personas_response.status_code == 200
    personas = personas_response.json()
    assert all(persona['id'].startswith('builtin:persona:') for persona in personas)
    persona = personas[0]
    assert persona['id'].startswith('builtin:persona:')
    assert persona['instructions']
    assert 'enabled' not in persona
    assert 'editable' not in persona

    assert skills_response.status_code == 200
    skills = skills_response.json()
    assert all(skill['id'].startswith('builtin:skill:') for skill in skills)
    skill = skills[0]
    assert skill['id'].startswith('builtin:skill:')
    assert skill['instructions']
    assert 'enabled' not in skill
    assert 'editable' not in skill


def test_catalog_routes_require_authentication() -> None:
    """Catalog reads remain protected API operations without workspace state."""

    client = TestClient(build_app(authenticated=False))

    response = client.get('/api/v1/catalog/providers')

    assert response.status_code == 401
    assert response.json()['detail']['code'] == 'authentication_required'
