"""SQLite persistence for user identities."""

from __future__ import annotations

import json

from src.models.pipeline import PipelineHarness
from src.models.user import (
    ConfiguredModelAvailability,
    UserSettings,
)
from src.models.user import UserDocument
from src.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.repositories.shared.datetime import parse_datetime


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
                SELECT id, created_at, updated_at, settings_json, username,
                       password_hash, role, is_active
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

    async def get_by_username(self, *, username: str) -> UserDocument | None:
        """Return one local account by its case-insensitive username."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, created_at, updated_at, settings_json, username,
                       password_hash, role, is_active
                FROM users
                WHERE lower(username) = lower(?)
                ''',
                (username,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_document(row) if row is not None else None

    async def has_local_accounts(self) -> bool:
        """Return whether any user has completed local-account setup."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                'SELECT EXISTS(SELECT 1 FROM users WHERE username IS NOT NULL)',
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return bool(row[0])

    async def create_if_absent(self, document: UserDocument) -> UserDocument:
        """Create a user or return the record already stored for its ID."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO users (
                        id, created_at, updated_at, settings_json, username,
                        password_hash, role, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO NOTHING
                    ''',
                    (
                        document.id,
                        document.created_at.isoformat(),
                        document.updated_at.isoformat(),
                        _settings_json(document.settings),
                        document.username,
                        document.password_hash,
                        document.role,
                        int(document.is_active),
                    ),
                )
                cursor = await connection.execute(
                    '''
                    SELECT id, created_at, updated_at, settings_json, username,
                           password_hash, role, is_active
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
                SET settings_json = ?, username = ?, password_hash = ?,
                    role = ?, is_active = ?, updated_at = ?
                WHERE id = ?
                RETURNING id, created_at, updated_at, settings_json, username,
                          password_hash, role, is_active
                ''',
                (
                    _settings_json(document.settings),
                    document.username,
                    document.password_hash,
                    document.role,
                    int(document.is_active),
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
        username=row['username'],
        password_hash=row['password_hash'],
        role=row['role'],
        is_active=bool(row['is_active']),
    )


def _settings_json(settings: UserSettings) -> str:
    """Serialize persisted settings using the shared Harness contract."""

    harness = settings.default_harness
    return json.dumps({
        'default_model_id': settings.default_model_id,
        'default_harness': (
            {
                'kind': harness.kind,
                'version': harness.version,
                'config': dict(harness.config),
            }
            if harness is not None
            else None
        ),
        'default_model_availability': settings.default_model_availability,
        'configured_models': [
            {
                'id': model.id,
                'status': model.status,
            }
            for model in settings.configured_models
        ],
    })


def _settings_from_json(value: str | None) -> UserSettings:
    """Rehydrate nullable User settings stored by SQLite."""

    if value is None:
        return UserSettings()
    payload = json.loads(value)
    harness = payload.get('default_harness')
    default_harness = (
        PipelineHarness(
            kind=harness['kind'],
            version=harness['version'],
            config=harness.get('config', {}),
        )
        if isinstance(harness, dict)
        else None
    )
    default_model_availability = payload.get('default_model_availability')
    configured_models = payload.get('configured_models')
    return UserSettings(
        default_model_id=(
            payload.get('default_model_id')
            if isinstance(payload.get('default_model_id'), str)
            else None
        ),
        default_harness=default_harness,
        default_model_availability=(
            default_model_availability
            if default_model_availability in ('enabled', 'disabled')
            else 'enabled'
        ),
        configured_models=tuple(
            ConfiguredModelAvailability(
                id=model['id'],
                status=model['status'],
            )
            for model in configured_models
            if isinstance(model, dict)
            and isinstance(model.get('id'), str)
            and model.get('status') in ('enabled', 'disabled')
        ) if isinstance(configured_models, list) else (),
    )
