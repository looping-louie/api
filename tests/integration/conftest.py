"""Shared fixtures for SQLite integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.bootstrap import configure_application
from src.middleware import DevelopmentAuthMiddleware
from src.repositories.infrastructure.migration_runner import (
    run_sqlite_migrations,
)
from src.repositories.infrastructure.sqlite_database import (
    SqliteDatabase,
)
from src.routers import api_v1_router
from src.services.providers.connection import HttpProviderConnectionService
from src.services.shared.settings import AppSettings
from src.utils.http import register_exception_handlers


WorkspaceMembershipSeed = tuple[str, str, bool]
WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest.fixture
def api_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Return a fully configured API client backed by temporary SQLite data."""

    async def skip_provider_connection_check(
        self: HttpProviderConnectionService,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Avoid external provider requests while testing local API behavior."""

        del self, args, kwargs

    monkeypatch.setattr(
        HttpProviderConnectionService,
        'test_connection',
        skip_provider_connection_check,
    )
    settings = AppSettings(
        encryption_key=Fernet.generate_key().decode('utf-8'),
        database_path=tmp_path / 'looping-louie-api.db',
        dev_auth_enabled=True,
        dev_user_id='local-user',
        catalog_strict_versioning=False,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Configure the production dependency graph for the test client."""

        await configure_application(app, settings=settings)
        yield

    app = FastAPI(lifespan=lifespan)
    register_exception_handlers(app)
    app.add_middleware(
        DevelopmentAuthMiddleware,
        user_id=settings.dev_user_id,
    )
    app.include_router(api_v1_router)

    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def sqlite_database_path(
    tmp_path: Path,
) -> AsyncIterator[Path]:
    """Create a migrated temporary SQLite database."""

    database_path = tmp_path / "looping-louie-test.db"

    await run_sqlite_migrations(
        database_path=database_path,
    )

    yield database_path


@pytest.fixture
def sqlite_database(
    sqlite_database_path: Path,
) -> SqliteDatabase:
    """Return the shared SQLite abstraction for the temporary database."""

    return SqliteDatabase(
        sqlite_database_path,
    )


@pytest.fixture
def create_workspace(
    sqlite_database_path: Path,
) -> WorkspaceFactory:
    """Return a helper that inserts projects and memberships."""

    async def create(
        *,
        project_id: str,
        name: str | None = None,
        memberships: Sequence[WorkspaceMembershipSeed] = (),
    ) -> None:
        timestamp = "2026-07-13T10:00:00+00:00"

        async with aiosqlite.connect(
            sqlite_database_path,
        ) as connection:
            await connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            await connection.execute(
                """
                INSERT INTO projects (
                    id,
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    project_id,
                    name or project_id,
                    timestamp,
                    timestamp,
                ),
            )

            if memberships:
                await connection.executemany(
                    '''
                    INSERT OR IGNORE INTO users (id, created_at, updated_at)
                    VALUES (?, ?, ?)
                    ''',
                    [
                        (user_id, timestamp, timestamp)
                        for user_id, _, _ in memberships
                    ],
                )
                await connection.executemany(
                    """
                    INSERT INTO project_memberships (
                        project_id,
                        user_id,
                        role,
                        is_default,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            project_id,
                            user_id,
                            role,
                            int(is_default),
                            timestamp,
                        )
                        for user_id, role, is_default in memberships
                    ],
                )

            await connection.commit()

    return create
