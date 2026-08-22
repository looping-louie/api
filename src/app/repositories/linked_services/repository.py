"""SQLite persistence for workspace-owned linked services."""

from __future__ import annotations

from typing import Protocol

import aiosqlite

from src.app.models.linked_service import LinkedService
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.shared.datetime import parse_datetime


class LinkedServiceRepository(Protocol):
    """Persistence operations required by LinkedServiceService."""

    async def list_for_workspace(self, workspace_id: str) -> list[LinkedService]:
        """Return linked services owned by a workspace."""
        raise NotImplementedError

    async def get(self, workspace_id: str, service_id: str) -> LinkedService | None:
        """Return one linked service when it belongs to the workspace."""
        raise NotImplementedError

    async def get_by_name(
        self,
        workspace_id: str,
        name: str,
    ) -> LinkedService | None:
        """Return one linked service matching a workspace-local name."""
        raise NotImplementedError

    async def create(self, linked_service: LinkedService) -> LinkedService:
        """Persist a new linked service."""
        raise NotImplementedError

    async def update(self, linked_service: LinkedService) -> LinkedService:
        """Persist mutable fields of an existing linked service."""
        raise NotImplementedError

    async def delete(self, workspace_id: str, service_id: str) -> bool:
        """Delete one workspace-owned linked service."""
        raise NotImplementedError


class SqliteLinkedServiceRepository:
    """SQLite implementation of linked-service persistence."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared SQLite connection manager."""
        self._database = database

    async def list_for_workspace(self, workspace_id: str) -> list[LinkedService]:
        """Return workspace services in stable name order."""
        async with self._database.connect() as connection:
            cursor = await connection.execute(
                f'{_SELECT} WHERE workspace_id = ? ORDER BY name ASC, id ASC',
                (workspace_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return [_row_to_linked_service(row) for row in rows]

    async def get(self, workspace_id: str, service_id: str) -> LinkedService | None:
        """Return one service only when it belongs to the requested workspace."""
        async with self._database.connect() as connection:
            cursor = await connection.execute(
                f'{_SELECT} WHERE workspace_id = ? AND id = ? LIMIT 1',
                (workspace_id, service_id),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _row_to_linked_service(row) if row is not None else None

    async def get_by_name(
        self,
        workspace_id: str,
        name: str,
    ) -> LinkedService | None:
        """Return one service identified by its workspace-local name."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                f'{_SELECT} WHERE workspace_id = ? AND name = ? LIMIT 1',
                (workspace_id, name),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _row_to_linked_service(row) if row is not None else None

    async def create(self, linked_service: LinkedService) -> LinkedService:
        """Insert a linked service and return its persisted representation."""
        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO linked_services (
                        id, workspace_id, name, provider_type, enabled,
                        key_trimmed, key_ciphertext, key_version, base_url,
                        version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    _values(linked_service),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return linked_service

    async def update(self, linked_service: LinkedService) -> LinkedService:
        """Update mutable linked-service fields without changing its identity."""
        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    UPDATE linked_services
                    SET name = ?, enabled = ?, key_trimmed = ?,
                        key_ciphertext = ?, key_version = ?, base_url = ?,
                        version = ?, updated_at = ?
                    WHERE workspace_id = ? AND id = ?
                    ''',
                    (
                        linked_service.name,
                        int(linked_service.enabled),
                        linked_service.key_trimmed,
                        linked_service.key_ciphertext,
                        linked_service.key_version,
                        linked_service.base_url,
                        linked_service.version,
                        linked_service.updated_at.isoformat(),
                        linked_service.workspace_id,
                        linked_service.id,
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return linked_service

    async def delete(self, workspace_id: str, service_id: str) -> bool:
        """Delete a service and report whether a row existed."""
        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                cursor = await connection.execute(
                    'DELETE FROM linked_services WHERE workspace_id = ? AND id = ?',
                    (workspace_id, service_id),
                )
                try:
                    deleted = cursor.rowcount == 1
                finally:
                    await cursor.close()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return deleted


_SELECT = '''
SELECT id, workspace_id, name, provider_type, enabled, key_trimmed,
       key_ciphertext, key_version, base_url, version, created_at, updated_at
FROM linked_services
'''


def _values(linked_service: LinkedService) -> tuple[object, ...]:
    """Convert a linked service to SQLite insert values."""
    return (
        linked_service.id,
        linked_service.workspace_id,
        linked_service.name,
        linked_service.provider_type,
        int(linked_service.enabled),
        linked_service.key_trimmed,
        linked_service.key_ciphertext,
        linked_service.key_version,
        linked_service.base_url,
        linked_service.version,
        linked_service.created_at.isoformat(),
        linked_service.updated_at.isoformat(),
    )


def _row_to_linked_service(row: aiosqlite.Row) -> LinkedService:
    """Convert a SQLite result row into a linked service."""
    return LinkedService(
        id=str(row['id']),
        workspace_id=str(row['workspace_id']),
        name=str(row['name']),
        provider_type=str(row['provider_type']),
        enabled=bool(row['enabled']),
        key_trimmed=str(row['key_trimmed']) if row['key_trimmed'] is not None else None,
        key_ciphertext=(
            str(row['key_ciphertext'])
            if row['key_ciphertext'] is not None
            else None
        ),
        key_version=int(row['key_version']),
        base_url=str(row['base_url']) if row['base_url'] is not None else None,
        version=int(row['version']),
        created_at=parse_datetime(row['created_at']),
        updated_at=parse_datetime(row['updated_at']),
    )
