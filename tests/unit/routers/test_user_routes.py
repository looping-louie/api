"""HTTP contract tests for current-user profile routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.controllers.user import UserController
from src.app.models.user import UserDocument
from src.app.routers.users import router
from src.app.services.users import UserService
from src.app.utils.http import register_exception_handlers


class FakeUserRepository:
    """Store user records in memory for route tests."""

    def __init__(self) -> None:
        """Initialize an empty user store."""

        self.documents: dict[str, UserDocument] = {}

    async def get(self, *, user_id: str) -> UserDocument | None:
        """Return the stored user for one identity."""

        return self.documents.get(user_id)

    async def create_if_absent(self, document: UserDocument) -> UserDocument:
        """Store a user only when its identity is new."""

        return self.documents.setdefault(document.id, document)

    async def update(self, document: UserDocument) -> UserDocument:
        """Replace the stored settings for one known identity."""

        self.documents[document.id] = document
        return document


def build_client() -> TestClient:
    """Build an application that accepts an explicit request user identity."""

    app = FastAPI()
    app.state.user_controller = UserController(
        service=UserService(
            repository=FakeUserRepository(),
            clock=lambda: datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
        ),
    )
    register_exception_handlers(app)
    app.include_router(router, prefix='/api/v1')
    return TestClient(app)


def test_register_then_get_returns_the_identified_user() -> None:
    """The explicit request identity is persisted as the current user."""

    client = build_client()
    headers = {'X-User-ID': 'user-1'}

    registered = client.post('/api/v1/users', headers=headers)
    retrieved = client.get('/api/v1/users/me', headers=headers)

    assert registered.status_code == 201
    assert retrieved.status_code == 200
    assert retrieved.json() == registered.json()
    assert registered.json()['id'] == 'user-1'
    assert registered.json()['settings'] == {
        'default_harness': None,
        'default_model_availability': 'enabled',
        'configured_models': [],
    }


def test_update_settings_persists_default_harness() -> None:
    """The current user can set and clear the inherited execution harness."""

    client = build_client()
    headers = {'X-User-ID': 'user-1'}
    client.post('/api/v1/users', headers=headers)

    updated = client.patch(
        '/api/v1/users/me',
        headers=headers,
        json={'default_harness': {'kind': 'codex_cli'}},
    )
    cleared = client.patch(
        '/api/v1/users/me',
        headers=headers,
        json={'default_harness': None},
    )

    assert updated.status_code == 200
    assert updated.json()['settings'] == {
        'default_harness': {'kind': 'codex_cli', 'version': 'v1', 'config': {}},
        'default_model_availability': 'enabled',
        'configured_models': [],
    }
    assert cleared.status_code == 200
    assert cleared.json()['settings'] == {
        'default_harness': None,
        'default_model_availability': 'enabled',
        'configured_models': [],
    }


def test_update_settings_persists_model_availability_policy() -> None:
    """Configured models override the default User availability policy."""

    client = build_client()
    headers = {'X-User-ID': 'user-1'}
    client.post('/api/v1/users', headers=headers)

    updated = client.patch(
        '/api/v1/users/me',
        headers=headers,
        json={
            'default_model_availability': 'disabled',
            'configured_models': [
                {'id': 'gpt-5', 'status': 'enabled'},
            ],
        },
    )

    assert updated.status_code == 200
    assert updated.json()['settings'] == {
        'default_harness': None,
        'default_model_availability': 'disabled',
        'configured_models': [{'id': 'gpt-5', 'status': 'enabled'}],
    }


def test_get_requires_registered_user() -> None:
    """Identifying a user does not silently create its profile."""

    response = build_client().get(
        '/api/v1/users/me',
        headers={'X-User-ID': 'user-1'},
    )

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'user_not_found'
