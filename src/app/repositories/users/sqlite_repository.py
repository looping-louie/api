"""SQLite persistence for user identities."""

from __future__ import annotations

import json

from src.app.models.pipeline import PipelineHarness
from src.app.models.user import UserSettings
from src.app.models.user import UserDocument
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.shared.datetime import parse_datetime


class SqliteUserRepository:
    """Persist API user identities in SQLite."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared SQLite connection manager."""

        self._database = database

    async def get(self, *, user_id: str) -> UserDocument | None:
        """Return one persisted user identity."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, created_at, updated_at, settings_json
                FROM users
                WHERE id = ?
                ''',
                (user_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_document(row) if row is not None else None

    async def create_if_absent(self, document: UserDocument) -> UserDocument:
        """Create a user or return the record already stored for its ID."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO users (id, created_at, updated_at, settings_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO NOTHING
                    ''',
                    (
                        document.id,
                        document.created_at.isoformat(),
                        document.updated_at.isoformat(),
                        _settings_json(document.settings),
                    ),
                )
                cursor = await connection.execute(
                    '''
                    SELECT id, created_at, updated_at, settings_json
                    FROM users
                    WHERE id = ?
                    ''',
                    (document.id,),
                )
                try:
                    row = await cursor.fetchone()
                finally:
                    await cursor.close()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        if row is None:
            raise RuntimeError('User creation did not return a stored user.')
        return _to_document(row)

    async def update(self, document: UserDocument) -> UserDocument:
        """Replace mutable settings for an existing user."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                UPDATE users
                SET settings_json = ?, updated_at = ?
                WHERE id = ?
                RETURNING id, created_at, updated_at, settings_json
                ''',
                (
                    _settings_json(document.settings),
                    document.updated_at.isoformat(),
                    document.id,
                ),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            await connection.commit()
        if row is None:
            raise RuntimeError('User update did not return a stored user.')
        return _to_document(row)


def _to_document(row: object) -> UserDocument:
    """Map a SQLite user row to the domain document."""

    return UserDocument(
        id=row['id'],
        created_at=parse_datetime(row['created_at']),
        updated_at=parse_datetime(row['updated_at']),
        settings=_settings_from_json(row['settings_json']),
    )


def _settings_json(settings: UserSettings) -> str:
    """Serialize persisted settings using the shared Harness contract."""

    harness = settings.default_harness
    return json.dumps({
        'default_harness': (
            {
                'kind': harness.kind,
                'version': harness.version,
                'config': dict(harness.config),
            }
            if harness is not None
            else None
        ),
    })


def _settings_from_json(value: str | None) -> UserSettings:
    """Rehydrate nullable User settings stored by SQLite."""

    if value is None:
        return UserSettings()
    payload = json.loads(value)
    harness = payload.get('default_harness')
    if not isinstance(harness, dict):
        return UserSettings()
    return UserSettings(default_harness=PipelineHarness(
        kind=harness['kind'],
        version=harness['version'],
        config=harness.get('config', {}),
    ))
