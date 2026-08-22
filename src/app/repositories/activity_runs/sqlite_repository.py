"""SQLite persistence for activity execution records."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.app.models.activity_run import ActivityRunDocument
from src.app.repositories.activity_runs.errors import (
    ActivityRunInvalidTransitionError,
    ActivityRunTokenConflictError,
)


class SqliteActivityRunRepository:
    """Persist activity execution records and checkpoint transitions."""

    def __init__(self, database_path: str | Path) -> None:
        """Store the SQLite database path used for connections."""

        self._database_path = Path(database_path)

    async def create(
        self,
        *,
        document: ActivityRunDocument,
    ) -> ActivityRunDocument:
        """Insert one initial activity execution and its checkpoint."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO activity_runs (
                        id, workspace_id, activity_id, input, status, state,
                        next_action, iteration, token_revision,
                        continuation_token, activity_snapshot_json,
                        execution_context_json, created_at, created_by,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        document.id,
                        document.workspace_id,
                        document.activity_id,
                        document.input,
                        document.status,
                        document.state,
                        document.next_action,
                        document.iteration,
                        document.token_revision,
                        document.continuation_token,
                        json.dumps(document.activity_snapshot, sort_keys=True),
                        json.dumps(document.execution_context, sort_keys=True),
                        document.created_at.isoformat(),
                        document.created_by,
                        document.updated_at.isoformat(),
                    ),
                )
                await self._insert_checkpoint(
                    connection,
                    document=document,
                    created_at=document.created_at,
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return document

    async def get(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        run_id: str,
    ) -> ActivityRunDocument | None:
        """Return one activity run when it belongs to the requested activity."""

        async with self._connect() as connection:
            row = await self._get_row(
                connection,
                workspace_id=workspace_id,
                activity_id=activity_id,
                run_id=run_id,
            )
        return self._to_document(row) if row is not None else None

    async def list(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[ActivityRunDocument], int]:
        """Return newest-first runs and their total for one activity."""

        async with self._connect() as connection:
            count_cursor = await connection.execute(
                'SELECT COUNT(*) AS total FROM activity_runs '
                'WHERE workspace_id = ? AND activity_id = ?',
                (workspace_id, activity_id),
            )
            try:
                count_row = await count_cursor.fetchone()
            finally:
                await count_cursor.close()
            cursor = await connection.execute(
                '''
                SELECT * FROM activity_runs
                WHERE workspace_id = ? AND activity_id = ?
                ORDER BY created_at DESC, id ASC
                LIMIT ? OFFSET ?
                ''',
                (workspace_id, activity_id, limit, offset),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        total = int(count_row['total']) if count_row is not None else 0
        return [self._to_document(row) for row in rows], total

    async def transition(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        expected_action: str,
        status: str,
        state: str,
        next_action: str,
        next_continuation_token: str | None,
        execution_context: dict[str, object],
        updated_at: datetime,
        iteration: int | None = None,
        pipeline_run_id: str | None = None,
        lease_token: str | None = None,
    ) -> ActivityRunDocument:
        """Persist one token-guarded checkpoint transition or its replay."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                row = await self._get_row(
                    connection,
                    workspace_id=workspace_id,
                    activity_id=activity_id,
                    run_id=run_id,
                )
                if row is None:
                    raise ActivityRunInvalidTransitionError()
                if not await self._has_active_pipeline_lease(
                    connection,
                    workspace_id=workspace_id,
                    activity_run_id=run_id,
                    pipeline_run_id=pipeline_run_id,
                    lease_token=lease_token,
                    now=updated_at,
                ):
                    raise ActivityRunInvalidTransitionError()
                revision = await self._get_checkpoint_revision(
                    connection,
                    workspace_id=workspace_id,
                    run_id=run_id,
                    continuation_token=continuation_token,
                )
                if revision is None:
                    raise ActivityRunTokenConflictError()
                replay = await self._get_idempotent_response(
                    connection,
                    workspace_id=workspace_id,
                    run_id=run_id,
                    token_revision=revision,
                    idempotency_key=idempotency_key,
                )
                if replay is not None:
                    await connection.commit()
                    return replay
                if int(row['token_revision']) != revision:
                    raise ActivityRunTokenConflictError()
                if str(row['next_action']) != expected_action:
                    raise ActivityRunInvalidTransitionError()
                updated = self._to_document(
                    row,
                    status=status,
                    state=state,
                    next_action=next_action,
                    iteration=iteration,
                    token_revision=revision + 1,
                    continuation_token=next_continuation_token,
                    execution_context=execution_context,
                    updated_at=updated_at,
                )
                await connection.execute(
                    '''
                    UPDATE activity_runs
                    SET status = ?, state = ?, next_action = ?, iteration = ?,
                        token_revision = ?, continuation_token = ?,
                        execution_context_json = ?, updated_at = ?
                    WHERE workspace_id = ? AND activity_id = ? AND id = ?
                    ''',
                    (
                        updated.status,
                        updated.state,
                        updated.next_action,
                        updated.iteration,
                        updated.token_revision,
                        updated.continuation_token,
                        json.dumps(updated.execution_context, sort_keys=True),
                        updated.updated_at.isoformat(),
                        workspace_id,
                        activity_id,
                        run_id,
                    ),
                )
                await self._insert_checkpoint(
                    connection,
                    document=updated,
                    created_at=updated.updated_at,
                )
                await self._store_idempotent_response(
                    connection,
                    workspace_id=workspace_id,
                    run_id=run_id,
                    token_revision=revision,
                    idempotency_key=idempotency_key,
                    document=updated,
                    created_at=updated.updated_at,
                )
                await connection.commit()
                return updated
            except Exception:
                await connection.rollback()
                raise

    async def has_active_pipeline_lease(
        self,
        *,
        workspace_id: str,
        activity_run_id: str,
        pipeline_run_id: str | None,
        lease_token: str | None,
        now: datetime,
    ) -> bool:
        """Return whether a Pipeline child has a valid current worker lease."""

        async with self._connect() as connection:
            return await self._has_active_pipeline_lease(
                connection,
                workspace_id=workspace_id,
                activity_run_id=activity_run_id,
                pipeline_run_id=pipeline_run_id,
                lease_token=lease_token,
                now=now,
            )

    @staticmethod
    async def _has_active_pipeline_lease(
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        activity_run_id: str,
        pipeline_run_id: str | None,
        lease_token: str | None,
        now: datetime,
    ) -> bool:
        """Allow standalone and human child runs, or fence runtime children."""

        cursor = await connection.execute(
            '''
            SELECT pipeline_run_id
            FROM pipeline_run_steps
            WHERE workspace_id = ? AND activity_run_id = ?
            ''',
            (workspace_id, activity_run_id),
        )
        try:
            owner = await cursor.fetchone()
        finally:
            await cursor.close()
        if owner is None:
            return True
        if (
            pipeline_run_id is None
            or str(owner['pipeline_run_id']) != pipeline_run_id
        ):
            return False
        cursor = await connection.execute(
            '''
            SELECT 1
            FROM pipeline_runs AS runs
            JOIN activity_runs AS child
                ON child.workspace_id = runs.workspace_id
                AND child.id = runs.current_activity_run_id
            WHERE runs.workspace_id = ? AND runs.id = ?
                AND runs.current_activity_run_id = ?
                            AND (
                    (runs.lease_token = ? AND runs.lease_expires_at > ?
                        AND runs.status IN ('claimed', 'in_progress'))
                    OR (runs.status = 'waiting' AND runs.lease_token IS NULL
                        AND child.state = 'awaiting_human_decision')
                            )
            ''',
            (
                workspace_id, pipeline_run_id, activity_run_id, lease_token,
                now.isoformat(),
            ),
        )
        try:
            return await cursor.fetchone() is not None
        finally:
            await cursor.close()

    @staticmethod
    def _to_document(
        row: aiosqlite.Row,
        *,
        status: str | None = None,
        state: str | None = None,
        next_action: str | None = None,
        iteration: int | None = None,
        token_revision: int | None = None,
        continuation_token: str | None | object = ...,
        execution_context: dict[str, object] | None = None,
        updated_at: datetime | None = None,
    ) -> ActivityRunDocument:
        """Map one persisted row into its domain representation."""

        return ActivityRunDocument(
            id=str(row['id']),
            workspace_id=str(row['workspace_id']),
            activity_id=str(row['activity_id']),
            input=str(row['input']),
            status=status or str(row['status']),
            state=state or str(row['state']),
            next_action=next_action or str(row['next_action']),
            iteration=iteration if iteration is not None else int(row['iteration']),
            token_revision=(
                token_revision
                if token_revision is not None
                else int(row['token_revision'])
            ),
            continuation_token=(
                str(row['continuation_token'])
                if continuation_token is ... and row['continuation_token'] is not None
                else continuation_token
            ),
            activity_snapshot=json.loads(str(row['activity_snapshot_json'])),
            execution_context=(
                execution_context
                if execution_context is not None
                else json.loads(str(row['execution_context_json']))
            ),
            created_at=datetime.fromisoformat(str(row['created_at'])),
            created_by=str(row['created_by']),
            updated_at=updated_at or datetime.fromisoformat(str(row['updated_at'])),
        )

    @staticmethod
    async def _get_row(
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        activity_id: str,
        run_id: str,
    ) -> aiosqlite.Row | None:
        """Return one activity-run row using the open transaction."""

        cursor = await connection.execute(
            'SELECT * FROM activity_runs '
            'WHERE workspace_id = ? AND activity_id = ? AND id = ?',
            (workspace_id, activity_id, run_id),
        )
        try:
            return await cursor.fetchone()
        finally:
            await cursor.close()

    @staticmethod
    async def _get_checkpoint_revision(
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        run_id: str,
        continuation_token: str,
    ) -> int | None:
        """Return the revision that issued a continuation token."""

        cursor = await connection.execute(
            'SELECT token_revision FROM activity_run_checkpoints '
            'WHERE workspace_id = ? AND run_id = ? AND continuation_token = ?',
            (workspace_id, run_id, continuation_token),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        return int(row['token_revision']) if row is not None else None

    @classmethod
    async def _get_idempotent_response(
        cls,
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        run_id: str,
        token_revision: int,
        idempotency_key: str,
    ) -> ActivityRunDocument | None:
        """Return a saved response for the same continuation request."""

        cursor = await connection.execute(
            'SELECT response_json FROM activity_run_idempotency '
            'WHERE workspace_id = ? AND run_id = ? AND token_revision = ? '
            'AND idempotency_key = ?',
            (workspace_id, run_id, token_revision, idempotency_key),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        return cls._document_from_json(json.loads(str(row['response_json']))) if row else None

    @staticmethod
    async def _insert_checkpoint(
        connection: aiosqlite.Connection,
        *,
        document: ActivityRunDocument,
        created_at: datetime,
    ) -> None:
        """Persist a checkpoint matching the supplied activity run state."""

        await connection.execute(
            '''
            INSERT INTO activity_run_checkpoints (
                workspace_id, run_id, token_revision, continuation_token,
                state, next_action, context_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                document.workspace_id,
                document.id,
                document.token_revision,
                document.continuation_token,
                document.state,
                document.next_action,
                json.dumps(document.execution_context, sort_keys=True),
                created_at.isoformat(),
            ),
        )

    @classmethod
    async def _store_idempotent_response(
        cls,
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        run_id: str,
        token_revision: int,
        idempotency_key: str,
        document: ActivityRunDocument,
        created_at: datetime,
    ) -> None:
        """Persist the exact response for a safe continuation replay."""

        await connection.execute(
            '''
            INSERT INTO activity_run_idempotency (
                workspace_id, run_id, token_revision, idempotency_key,
                response_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                workspace_id,
                run_id,
                token_revision,
                idempotency_key,
                json.dumps(cls._document_to_json(document), sort_keys=True),
                created_at.isoformat(),
            ),
        )

    @staticmethod
    def _document_to_json(document: ActivityRunDocument) -> dict[str, object]:
        """Serialize an activity run for idempotency storage."""

        return {
            'id': document.id,
            'workspace_id': document.workspace_id,
            'activity_id': document.activity_id,
            'input': document.input,
            'status': document.status,
            'state': document.state,
            'next_action': document.next_action,
            'iteration': document.iteration,
            'token_revision': document.token_revision,
            'continuation_token': document.continuation_token,
            'activity_snapshot': dict(document.activity_snapshot),
            'execution_context': dict(document.execution_context),
            'created_at': document.created_at.isoformat(),
            'created_by': document.created_by,
            'updated_at': document.updated_at.isoformat(),
        }

    @staticmethod
    def _document_from_json(value: dict[str, object]) -> ActivityRunDocument:
        """Restore an activity run from an idempotency response."""

        return ActivityRunDocument(
            id=str(value['id']),
            workspace_id=str(value['workspace_id']),
            activity_id=str(value['activity_id']),
            input=str(value['input']),
            status=str(value['status']),
            state=str(value['state']),
            next_action=str(value['next_action']),
            iteration=int(value['iteration']),
            token_revision=int(value['token_revision']),
            continuation_token=(
                str(value['continuation_token'])
                if value['continuation_token'] is not None
                else None
            ),
            activity_snapshot=dict(value['activity_snapshot']),
            execution_context=dict(value['execution_context']),
            created_at=datetime.fromisoformat(str(value['created_at'])),
            created_by=str(value['created_by']),
            updated_at=datetime.fromisoformat(str(value['updated_at'])),
        )

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Open one SQLite connection with foreign keys enabled."""

        connection = await aiosqlite.connect(self._database_path)
        connection.row_factory = aiosqlite.Row
        try:
            await connection.execute('PRAGMA foreign_keys = ON')
            yield connection
        finally:
            await connection.close()
