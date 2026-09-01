"""SQLite persistence for workspace runtime worker registration."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Mapping

from src.app.models.worker import (
    WorkerDocument,
    WorkerHarnessCapability,
    WorkerReadinessDocument,
)
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
                        id, project_id, registered_at, last_heartbeat_at,
                        harnesses_json
                    ) VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        document.id,
                        document.project_id,
                        document.registered_at.isoformat(),
                        document.last_heartbeat_at.isoformat(),
                        _serialize_harnesses(document.harnesses),
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return document

    async def get(
        self,
        *,
        project_id: str,
        worker_id: str,
    ) -> WorkerDocument | None:
        """Return one Worker registration and its reported capabilities."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, project_id, registered_at, last_heartbeat_at,
                    harnesses_json
                FROM workers
                WHERE project_id = ? AND id = ?
                ''',
                (project_id, worker_id),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_document(row) if row is not None else None

    async def heartbeat(
        self,
        *,
        project_id: str,
        worker_id: str,
        occurred_at: datetime,
        harnesses: tuple[WorkerHarnessCapability, ...] | None = None,
    ) -> WorkerDocument | None:
        """Refresh an existing worker and its currently observed capabilities."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                cursor = await connection.execute(
                    '''
                    UPDATE workers
                    SET last_heartbeat_at = ?,
                        harnesses_json = COALESCE(?, harnesses_json)
                    WHERE project_id = ? AND id = ?
                    RETURNING id, project_id, registered_at, last_heartbeat_at,
                        harnesses_json
                    ''',
                    (
                        occurred_at.isoformat(),
                        _serialize_harnesses(harnesses) if harnesses is not None else None,
                        project_id,
                        worker_id,
                    ),
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
        project_id: str,
        worker_id: str,
        active_since: datetime,
    ) -> bool:
        """Return whether the worker has heartbeated since the cutoff."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT 1 FROM workers
                WHERE project_id = ? AND id = ? AND last_heartbeat_at >= ?
                ''',
                (project_id, worker_id, active_since.isoformat()),
            )
            try:
                return await cursor.fetchone() is not None
            finally:
                await cursor.close()

    async def readiness(
        self,
        *,
        project_id: str,
        active_since: datetime,
        harness: Mapping[str, object],
    ) -> WorkerReadinessDocument:
        """Aggregate recent workers and exact Harness matches for a workspace."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, project_id, registered_at, last_heartbeat_at,
                    harnesses_json
                FROM workers
                WHERE project_id = ?
                ''',
                (project_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        workers = [_to_document(row) for row in rows]
        active = [
            worker for worker in workers
            if worker.last_heartbeat_at >= active_since
        ]
        compatible = [
            worker for worker in active
            if any(
                capability.kind == harness.get('kind')
                and capability.version == harness.get('version')
                and dict(capability.config) == harness.get('config')
                for capability in worker.harnesses
            )
        ]
        return WorkerReadinessDocument(
            registered_worker_count=len(workers),
            active_worker_count=len(active),
            compatible_worker_count=len(compatible),
            latest_heartbeat_at=max(
                (worker.last_heartbeat_at for worker in workers),
                default=None,
            ),
        )


def _to_document(row: object) -> WorkerDocument:
    """Map one SQLite worker row to the domain document."""

    from src.app.repositories.shared.datetime import parse_datetime

    return WorkerDocument(
        id=row['id'],
        project_id=row['project_id'],
        registered_at=parse_datetime(row['registered_at']),
        last_heartbeat_at=parse_datetime(row['last_heartbeat_at']),
        harnesses=_deserialize_harnesses(row['harnesses_json']),
    )


def _serialize_harnesses(
    harnesses: tuple[WorkerHarnessCapability, ...],
) -> str:
    """Serialize Worker capabilities in the durable API representation."""

    return json.dumps([
        {
            'kind': harness.kind,
            'version': harness.version,
            'config': dict(harness.config),
        }
        for harness in harnesses
    ])


def _deserialize_harnesses(value: str) -> tuple[WorkerHarnessCapability, ...]:
    """Decode the supported Worker Harness capability representation."""

    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise RuntimeError('Worker Harness capabilities are invalid.') from error
    if not isinstance(parsed, list):
        raise RuntimeError('Worker Harness capabilities are invalid.')
    capabilities: list[WorkerHarnessCapability] = []
    for capability in parsed:
        config = capability.get('config') if isinstance(capability, dict) else None
        if (
            not isinstance(capability, dict)
            or capability.get('kind') not in ('louie', 'codex_cli')
            or capability.get('version') != 'v1'
            or not isinstance(config, dict)
            or config
        ):
            raise RuntimeError('Worker Harness capabilities are invalid.')
        capabilities.append(WorkerHarnessCapability(kind=capability['kind']))
    return tuple(capabilities)
