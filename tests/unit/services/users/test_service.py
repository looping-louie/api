"""Tests for current-user profile operations."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.models.user import UserDocument
from src.services.users import UserNotFoundError, UserService


class FakeUserRepository:
    """Store user records in memory for service tests."""

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
        """Replace one stored user profile."""

        self.documents[document.id] = document
        return document


def build_service(repository: FakeUserRepository) -> UserService:
    """Build a user service with a deterministic clock."""

    return UserService(
        repository=repository,
        clock=lambda: datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_register_creates_a_durable_user_profile() -> None:
    """Registering an identified user creates its minimal durable profile."""

    repository = FakeUserRepository()

    document = await build_service(repository).register(user_id=' user-1 ')

    assert document.id == 'user-1'
    assert repository.documents['user-1'] == document


@pytest.mark.asyncio
async def test_register_preserves_an_existing_profile() -> None:
    """Repeated registration preserves the original user timestamps."""

    repository = FakeUserRepository()
    service = build_service(repository)

    registered = await service.register(user_id='user-1')
    repeated = await service.register(user_id='user-1')

    assert repeated == registered


@pytest.mark.asyncio
async def test_get_rejects_an_unregistered_identity() -> None:
    """An identity has no profile until it has registered."""

    with pytest.raises(UserNotFoundError):
        await build_service(FakeUserRepository()).get(user_id='user-1')


@pytest.mark.asyncio
async def test_settings_update_preserves_local_account_credentials() -> None:
    """Execution settings updates must not erase the login account fields."""

    repository = FakeUserRepository()
    existing = UserDocument(
        id='user-1',
        username='administrator',
        password_hash='argon2id.hash',
        role='admin',
        created_at=datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
    )
    repository.documents[existing.id] = existing

    updated = await build_service(repository).update_settings(
        user_id='user-1',
        default_model_id=None,
        default_harness=None,
        default_model_availability='enabled',
        configured_models=(),
    )

    assert updated.username == existing.username
    assert updated.password_hash == existing.password_hash
    assert updated.role == existing.role
