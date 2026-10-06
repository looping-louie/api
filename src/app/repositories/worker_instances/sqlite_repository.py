"""SQLite persistence for global Workers and Project enablements."""

from __future__ import annotations

import json

from src.app.models.worker import WorkerHarnessCapability
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
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
                SELECT id, registered_at, last_heartbeat_at, harnesses_json
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
                        id, registered_at, last_heartbeat_at, harnesses_json
                    ) VALUES (?, ?, ?, ?)
                    ''',
                    (
                        document.id,
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
                    INSERT INTO worker_project_enablements (
                        worker_instance_id, project_id, enabled_at
                    ) VALUES (?, ?, ?)
                    ''',
                    (
                        document.worker_instance_id,
                        document.project_id,
                        document.enabled_at.isoformat(),
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return document

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