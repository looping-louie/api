"""Tests for local-account authentication and opaque session issuance."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.models.user import UserDocument
from src.models.user_session import UserSession
from src.services.authentication import (
    AccountAuthenticationService,
    AuthenticationError,
    BootstrapUnavailableError,
    PasswordHasher,
)


class FakeUserRepository:
    """Store local-account documents for authentication tests."""

    def __init__(self) -> None:
        """Create the legacy local user without an account credential."""

        timestamp = datetime(2026, 11, 5, tzinfo=UTC)
        self.documents = {
            'local-user': UserDocument(
                id='local-user',
                created_at=timestamp,
                updated_at=timestamp,
            ),
        }

    async def get(self, *, user_id: str) -> UserDocument | None:
        """Return one document by ID."""

        return self.documents.get(user_id)

    async def get_by_username(self, *, username: str) -> UserDocument | None:
        """Return one document by username without case sensitivity."""

        return next(
            (
                document
                for document in self.documents.values()
                if document.username is not None
                and document.username.casefold() == username.casefold()
            ),
            None,
        )

    async def has_local_accounts(self) -> bool:
        """Return whether setup has assigned any local-account username."""

        return any(
            document.username is not None
            for document in self.documents.values()
        )

    async def update(self, document: UserDocument) -> UserDocument:
        """Replace one stored user document."""

        self.documents[document.id] = document
        return document


class FakeSessionRepository:
    """Record opaque session documents."""

    def __init__(self) -> None:
        """Initialize session recording."""

        self.sessions: list[UserSession] = []

    async def create(self, session: UserSession) -> UserSession:
        """Record one session."""

        self.sessions.append(session)
        return session


def build_service(
    users: FakeUserRepository,
    sessions: FakeSessionRepository,
) -> AccountAuthenticationService:
    """Build deterministic account authentication dependencies."""

    identifiers = iter(('session-1', 'session-2'))
    return AccountAuthenticationService(
        users=users,
        sessions=sessions,
        password_hasher=PasswordHasher(),
        id_factory=lambda: next(identifiers),
        token_factory=lambda: 'raw-session-token',
        clock=lambda: datetime(2026, 11, 5, tzinfo=UTC),
    )


def test_password_hasher_uses_argon2id_and_rejects_wrong_password() -> None:
    """Encoded Argon2id hashes verify only their original password."""

    password_hash = PasswordHasher().hash('long-enough-password')

    assert password_hash.startswith('argon2id.')
    assert PasswordHasher().verify(
        password='long-enough-password',
        encoded_hash=password_hash,
    )
    assert not PasswordHasher().verify(
        password='wrong-password',
        encoded_hash=password_hash,
    )


@pytest.mark.asyncio
async def test_bootstrap_upgrades_legacy_user_and_issues_session() -> None:
    """First setup retains existing local-user ownership and creates an admin."""

    users = FakeUserRepository()
    sessions = FakeSessionRepository()

    user, token = await build_service(users, sessions).bootstrap_administrator(
        username='administrator',
        password='long-enough-password',
    )

    assert user.id == 'local-user'
    assert user.username == 'administrator'
    assert user.role == 'admin'
    assert token == 'raw-session-token'
    assert sessions.sessions[0].user_id == 'local-user'
    assert sessions.sessions[0].token_hash != token


@pytest.mark.asyncio
async def test_bootstrap_cannot_replace_existing_local_account() -> None:
    """A completed setup cannot silently replace the instance administrator."""

    users = FakeUserRepository()
    sessions = FakeSessionRepository()
    service = build_service(users, sessions)
    await service.bootstrap_administrator(
        username='administrator',
        password='long-enough-password',
    )

    with pytest.raises(BootstrapUnavailableError):
        await service.bootstrap_administrator(
            username='replacement',
            password='another-long-password',
        )


@pytest.mark.asyncio
async def test_authentication_rejects_unknown_or_invalid_credentials() -> None:
    """Login failures do not disclose whether the username exists."""

    users = FakeUserRepository()
    sessions = FakeSessionRepository()
    service = build_service(users, sessions)
    await service.bootstrap_administrator(
        username='administrator',
        password='long-enough-password',
    )

    with pytest.raises(AuthenticationError):
        await service.authenticate(
            username='administrator',
            password='wrong-password',
        )
    with pytest.raises(AuthenticationError):
        await service.authenticate(
            username='unknown',
            password='long-enough-password',
        )
