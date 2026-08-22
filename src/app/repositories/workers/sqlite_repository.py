"""SQLite persistence for workspace runtime worker registration."""

from __future__ import annotations

from datetime import datetime

from src.app.models.worker import WorkerDocument
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase


class SqliteWorkerRepository:
    """Persist API-owned workspace runtime worker identities."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared SQLite connection manager."""

        self._database = database

    async def create(self, document: WorkerDocument) -> WorkerDocument:
        """Persist one newly provisioned worker identity."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO workers (
                        id, workspace_id, registered_at, last_heartbeat_at
                    ) VALUES (?, ?, ?, ?)
                    ''',
                    (
                        document.id,
                        document.workspace_id,
                        document.registered_at.isoformat(),
                        document.last_heartbeat_at.isoformat(),
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return document

    async def heartbeat(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        occurred_at: datetime,
    ) -> WorkerDocument | None:
        """Refresh an existing worker and return its current registration."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                cursor = await connection.execute(
                    '''
                    UPDATE workers
                    SET last_heartbeat_at = ?
                    WHERE workspace_id = ? AND id = ?
                    RETURNING id, workspace_id, registered_at, last_heartbeat_at
                    ''',
                    (occurred_at.isoformat(), workspace_id, worker_id),
                )
                try:
                    row = await cursor.fetchone()
                finally:
                    await cursor.close()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return _to_document(row) if row is not None else None

    async def is_active(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        active_since: datetime,
    ) -> bool:
        """Return whether the worker has heartbeated since the cutoff."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT 1 FROM workers
                WHERE workspace_id = ? AND id = ? AND last_heartbeat_at >= ?
                ''',
                (workspace_id, worker_id, active_since.isoformat()),
            )
            try:
                return await cursor.fetchone() is not None
            finally:
                await cursor.close()


def _to_document(row: object) -> WorkerDocument:
    """Map one SQLite worker row to the domain document."""

    from src.app.repositories.shared.datetime import parse_datetime

    return WorkerDocument(
        id=row['id'],
        workspace_id=row['workspace_id'],
        registered_at=parse_datetime(row['registered_at']),
        last_heartbeat_at=parse_datetime(row['last_heartbeat_at']),
    )
