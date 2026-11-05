"""Integration tests for local accounts and server-side sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.models.user import UserDocument
from src.models.user_session import UserSession
from src.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.repositories.user_sessions import SqliteUserSessionRepository
from src.repositories.users import SqliteUserRepository


@pytest.mark.asyncio
async def test_user_repository_persists_local_account_fields(
    sqlite_database_path: Path,
) -> None:
    """Local account lookup preserves credentials, role, and activation state."""

    repository = SqliteUserRepository(SqliteDatabase(sqlite_database_path))
    timestamp = datetime(2026, 11, 5, tzinfo=UTC)
    document = UserDocument(
        id='user-1',
        username='Administrator',
        password_hash='argon2id$hash',
        role='admin',
        is_active=True,
        created_at=timestamp,
        updated_at=timestamp,
    )

    await repository.create_if_absent(document)

    assert await repository.get_by_username(username='administrator') == document


@pytest.mark.asyncio
async def test_session_repository_persists_and_revokes_token_digests(
    sqlite_database_path: Path,
) -> None:
    """Sessions are selected and revoked by the digest rather than a raw token."""

    database = SqliteDatabase(sqlite_database_path)
    users = SqliteUserRepository(database)
    sessions = SqliteUserSessionRepository(database)
    timestamp = datetime(2026, 11, 5, tzinfo=UTC)
    await users.create_if_absent(UserDocument(
        id='user-1',
        created_at=timestamp,
        updated_at=timestamp,
    ))
    session = UserSession(
        id='session-1',
        user_id='user-1',
        token_hash='sha256-digest',
        created_at=timestamp,
        last_seen_at=timestamp,
        expires_at=timestamp + timedelta(days=1),
    )

    await sessions.create(session)

    assert await sessions.get_by_token_hash(
        token_hash='sha256-digest',
    ) == session
    await sessions.delete_by_token_hash(token_hash='sha256-digest')
    assert await sessions.get_by_token_hash(token_hash='sha256-digest') is None
