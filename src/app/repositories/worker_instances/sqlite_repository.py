"""SQLite persistence for Workers and Project enablements."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Mapping

from src.app.models.worker import WorkerHarnessCapability, WorkerReadinessDocument
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerInstanceProjectDocument,
    WorkerProjectEnablementDocument,
)
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.shared.datetime import parse_datetime


class SqliteWorkerInstanceRepository:
    """Persist Worker identities separately from their Project assignments."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared SQLite connection manager."""

        self._database = database

    async def get(
        self,
        *,
        worker_instance_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return one Worker and its advertised Harnesses."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, owner_user_id, registered_at, last_heartbeat_at,
                    harnesses_json
                FROM worker_instances
                WHERE id = ?
                ''',
                (worker_instance_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_worker_document(row) if row is not None else None

    async def get_for_owner(
        self,
        *,
        worker_instance_id: str,
        owner_user_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return one Worker owned by the specified User."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, owner_user_id, registered_at, last_heartbeat_at,
                    harnesses_json
                FROM worker_instances
                WHERE id = ? AND owner_user_id = ?
                ''',
                (worker_instance_id, owner_user_id),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_worker_document(row) if row is not None else None

    async def create(
        self,
        document: WorkerInstanceDocument,
    ) -> WorkerInstanceDocument:
        """Persist one Worker and its advertised Harnesses."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO worker_instances (
                        id, owner_user_id, registered_at, last_heartbeat_at,
                        harnesses_json
                    ) VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        document.id,
                        document.owner_user_id,
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

    async def heartbeat(
        self,
        *,
        worker_instance_id: str,
        occurred_at: datetime,
        harnesses: tuple[WorkerHarnessCapability, ...],
    ) -> WorkerInstanceDocument | None:
        """Refresh one Worker's liveness and observed Harnesses."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                cursor = await connection.execute(
                    '''
                    UPDATE worker_instances
                    SET last_heartbeat_at = ?, harnesses_json = ?
                    WHERE id = ?
                    RETURNING id, owner_user_id, registered_at,
                        last_heartbeat_at, harnesses_json
                    ''',
                    (
                        occurred_at.isoformat(),
                        _serialize_harnesses(harnesses),
                        worker_instance_id,
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
        return _to_worker_document(row) if row is not None else None

    async def get_enabled(
        self,
        *,
        worker_instance_id: str,
        project_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return a Worker only when it is enabled for the Project."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT worker.id, worker.registered_at, worker.last_heartbeat_at,
                    worker.owner_user_id, worker.harnesses_json
                FROM worker_instances AS worker
                INNER JOIN worker_project_enablements AS enablement
                    ON enablement.worker_instance_id = worker.id
                WHERE worker.id = ? AND enablement.project_id = ?
                ''',
                (worker_instance_id, project_id),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_worker_document(row) if row is not None else None

    async def readiness(
        self,
        *,
        project_id: str,
        active_since: datetime,
        harness: Mapping[str, object],
    ) -> WorkerReadinessDocument:
        """Summarize enabled Worker liveness and exact Harness matches."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT worker.id, worker.registered_at, worker.last_heartbeat_at,
                    worker.owner_user_id, worker.harnesses_json
                FROM worker_instances AS worker
                INNER JOIN worker_project_enablements AS enablement
                    ON enablement.worker_instance_id = worker.id
                WHERE enablement.project_id = ?
                ''',
                (project_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        workers = [_to_worker_document(row) for row in rows]
        active = [
            worker for worker in workers
            if worker.last_heartbeat_at >= active_since
        ]
        compatible = [
            worker for worker in active
            if any(capability.matches(harness) for capability in worker.harnesses)
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

    async def enable_project(
        self,
        document: WorkerProjectEnablementDocument,
    ) -> WorkerProjectEnablementDocument:
        """Persist one Worker's Project execution authorization."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT OR IGNORE INTO worker_project_enablements (
                        worker_instance_id, project_id, enabled_at
                    ) VALUES (?, ?, ?)
                    ''',
                    (
                        document.worker_instance_id,
                        document.project_id,
                        document.enabled_at.isoformat(),
                    ),
                )
                cursor = await connection.execute(
                    '''
                    SELECT worker_instance_id, project_id, enabled_at
                    FROM worker_project_enablements
                    WHERE worker_instance_id = ? AND project_id = ?
                    ''',
                    (document.worker_instance_id, document.project_id),
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
            raise RuntimeError('Worker Project enablement was not persisted.')
        return _to_enablement_document(row)

    async def list_enabled_projects(
        self,
        *,
        worker_instance_id: str,
    ) -> tuple[WorkerProjectEnablementDocument, ...]:
        """Return all Project assignments for one Worker."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT worker_instance_id, project_id, enabled_at
                FROM worker_project_enablements
                WHERE worker_instance_id = ?
                ORDER BY project_id
                ''',
                (worker_instance_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return tuple(_to_enablement_document(row) for row in rows)

    async def list_enabled(
        self,
        *,
        project_id: str,
    ) -> tuple[WorkerInstanceProjectDocument, ...]:
        """Return Workers enabled for one Project."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT worker.id, worker.registered_at, worker.last_heartbeat_at,
                    worker.owner_user_id, worker.harnesses_json,
                    enablement.worker_instance_id,
                    enablement.project_id, enablement.enabled_at
                FROM worker_project_enablements AS enablement
                INNER JOIN worker_instances AS worker
                    ON worker.id = enablement.worker_instance_id
                WHERE enablement.project_id = ?
                ORDER BY worker.last_heartbeat_at DESC, worker.id
                ''',
                (project_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return tuple(
            WorkerInstanceProjectDocument(
                worker=_to_worker_document(row),
                enablement=_to_enablement_document(row),
            )
            for row in rows
        )


def _serialize_harnesses(
    harnesses: tuple[WorkerHarnessCapability, ...],
) -> str:
    """Serialize Harness capabilities in the durable API representation."""

    return json.dumps([
        {
            'kind': harness.kind,
            'version': harness.version,
            'config': dict(harness.config),
        }
        for harness in harnesses
    ])


def _to_enablement_document(row: object) -> WorkerProjectEnablementDocument:
    """Map one SQLite enablement row to its domain document."""

    return WorkerProjectEnablementDocument(
        worker_instance_id=row['worker_instance_id'],
        project_id=row['project_id'],
        enabled_at=parse_datetime(row['enabled_at']),
    )


def _to_worker_document(row: object) -> WorkerInstanceDocument:
    """Map one SQLite Worker row to its domain document."""

    return WorkerInstanceDocument(
        id=row['id'],
        owner_user_id=row['owner_user_id'],
        registered_at=parse_datetime(row['registered_at']),
        last_heartbeat_at=parse_datetime(row['last_heartbeat_at']),
        harnesses=_deserialize_harnesses(row['harnesses_json']),
    )


def _deserialize_harnesses(value: str) -> tuple[WorkerHarnessCapability, ...]:
    """Decode the durable Worker Harness capability representation."""

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
            or capability.get('kind') not in ('louie', 'codex_cli', 'copilot_cli')
            or capability.get('version') != 'v1'
            or not isinstance(config, dict)
            or config
        ):
            raise RuntimeError('Worker Harness capabilities are invalid.')
        capabilities.append(WorkerHarnessCapability(kind=capability['kind']))
    return tuple(capabilities)
