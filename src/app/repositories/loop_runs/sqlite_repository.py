"""SQLite persistence for loop execution records."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.app.models.loop_run import LoopRunDocument

from .errors import LoopRunInvalidTransitionError, LoopRunTokenConflictError


class SqliteLoopRunRepository:
    """Persist loop runs independently from pipeline execution state."""

    def __init__(self, database_path: str | Path) -> None:
        """Store the SQLite database path used for connections."""

        self._database_path = Path(database_path)

    async def has_runs(
        self,
        *,
        workspace_id: str,
        loop_id: str,
    ) -> bool:
        """Return whether the selected loop has persisted executions."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT EXISTS(
                    SELECT 1 FROM loop_runs
                    WHERE workspace_id = ? AND loop_id = ?
                ) AS has_runs
                ''',
                (workspace_id, loop_id),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return bool(row['has_runs']) if row is not None else False

    async def create(self, *, document: LoopRunDocument) -> LoopRunDocument:
        """Insert one initial loop execution record."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO loop_runs (
                        id, workspace_id, loop_id, input, status, state,
                        next_action, iteration, token_revision,
                        continuation_token, loop_snapshot_json,
                        execution_context_json, created_at, created_by,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        document.id,
                        document.workspace_id,
                        document.loop_id,
                        document.input,
                        document.status,
                        document.state,
                        document.next_action,
                        document.iteration,
                        document.token_revision,
                        document.continuation_token,
                        json.dumps(document.loop_snapshot, sort_keys=True),
                        json.dumps(document.execution_context, sort_keys=True),
                        self._serialize_datetime(document.created_at),
                        document.created_by,
                        self._serialize_datetime(document.updated_at),
                    ),
                )
                await connection.execute(
                    '''
                    INSERT INTO loop_run_checkpoints (
                        workspace_id, run_id, token_revision,
                        continuation_token, state, next_action,
                        context_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        document.workspace_id,
                        document.id,
                        document.token_revision,
                        document.continuation_token,
                        document.state,
                        document.next_action,
                        json.dumps(document.execution_context, sort_keys=True),
                        self._serialize_datetime(document.created_at),
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
        workspace_id: str,
        loop_id: str,
        run_id: str,
    ) -> LoopRunDocument | None:
        """Return one loop run belonging to the requested loop."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT *
                FROM loop_runs
                WHERE workspace_id = ? AND loop_id = ? AND id = ?
                ''',
                (workspace_id, loop_id, run_id),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return self._to_document(row) if row is not None else None

    async def list(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[LoopRunDocument], int]:
        """Return newest-first loop runs and their total count."""
        async with self._connect() as connection:
            count_cursor = await connection.execute(
                '''
                SELECT COUNT(*) AS total
                FROM loop_runs
                WHERE workspace_id = ? AND loop_id = ?
                ''',
                (workspace_id, loop_id),
            )
            try:
                count_row = await count_cursor.fetchone()
            finally:
                await count_cursor.close()
            cursor = await connection.execute(
                '''
                SELECT *
                FROM loop_runs
                WHERE workspace_id = ? AND loop_id = ?
                ORDER BY created_at DESC, id ASC
                LIMIT ? OFFSET ?
                ''',
                (workspace_id, loop_id, limit, offset),
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
        loop_id: str,
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
    ) -> LoopRunDocument:
        """Persist one checkpoint transition with token and replay protection."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                row = await self._get_row(
                    connection,
                    workspace_id=workspace_id,
                    loop_id=loop_id,
                    run_id=run_id,
                )
                if row is None:
                    await connection.rollback()
                    raise LoopRunInvalidTransitionError()

                revision = await self._get_checkpoint_revision(
                    connection,
                    workspace_id=workspace_id,
                    run_id=run_id,
                    continuation_token=continuation_token,
                )
                if revision is None:
                    await connection.rollback()
                    raise LoopRunTokenConflictError()
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
                    await connection.rollback()
                    raise LoopRunTokenConflictError()
                if str(row['next_action']) != expected_action:
                    await connection.rollback()
                    raise LoopRunInvalidTransitionError()

                updated = self._to_document(
                    row,
                    status=status,
                    state=state,
                    next_action=next_action,
                    iteration=iteration if iteration is not None else int(row['iteration']),
                    token_revision=revision + 1,
                    continuation_token=next_continuation_token,
                    execution_context=execution_context,
                    updated_at=updated_at,
                )
                await connection.execute(
                    '''
                    UPDATE loop_runs
                    SET status = ?, state = ?, next_action = ?, iteration = ?, token_revision = ?,
                        continuation_token = ?, execution_context_json = ?,
                        updated_at = ?
                    WHERE workspace_id = ? AND loop_id = ? AND id = ?
                    ''',
                    (
                        status,
                        updated.state,
                        updated.next_action,
                        updated.iteration,
                        updated.token_revision,
                        updated.continuation_token,
                        json.dumps(execution_context, sort_keys=True),
                        self._serialize_datetime(updated.updated_at),
                        workspace_id,
                        loop_id,
                        run_id,
                    ),
                )
                await connection.execute(
                    '''
                    INSERT INTO loop_run_checkpoints (
                        workspace_id, run_id, token_revision,
                        continuation_token, state, next_action,
                        context_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        workspace_id,
                        run_id,
                        updated.token_revision,
                        updated.continuation_token,
                        updated.state,
                        updated.next_action,
                        json.dumps(execution_context, sort_keys=True),
                        self._serialize_datetime(updated.updated_at),
                    ),
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

    async def continue_collect_snapshot(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        execution_context: dict[str, object],
        updated_at: datetime,
    ) -> LoopRunDocument:
        """Preserve the initial checkpoint transition for existing callers."""

        return await self.transition(
            workspace_id=workspace_id,
            loop_id=loop_id,
            run_id=run_id,
            continuation_token=continuation_token,
            idempotency_key=idempotency_key,
            expected_action='collect_snapshot',
            status='in_progress',
            state='awaiting_generation',
            next_action='none',
            next_continuation_token=None,
            execution_context=execution_context,
            updated_at=updated_at,
        )

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
    ) -> LoopRunDocument:
        """Map one persisted loop-run row into its domain representation."""

        return LoopRunDocument(
            id=str(row['id']),
            workspace_id=str(row['workspace_id']),
            loop_id=str(row['loop_id']),
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
                if continuation_token is ...
                and row['continuation_token'] is not None
                else continuation_token
            ),
            loop_snapshot=json.loads(str(row['loop_snapshot_json'])),
            execution_context=(
                execution_context
                if execution_context is not None
                else json.loads(str(row['execution_context_json']))
            ),
            created_at=datetime.fromisoformat(str(row['created_at'])),
            created_by=str(row['created_by']),
            updated_at=(
                updated_at
                if updated_at is not None
                else datetime.fromisoformat(str(row['updated_at']))
            ),
        )

    @staticmethod
    async def _get_row(
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
    ) -> aiosqlite.Row | None:
        """Return one loop-run row using the open transaction."""

        cursor = await connection.execute(
            '''
            SELECT * FROM loop_runs
            WHERE workspace_id = ? AND loop_id = ? AND id = ?
            ''',
            (workspace_id, loop_id, run_id),
        )
        try:
            return await cursor.fetchone()
        finally:
            await cursor.close()

    @classmethod
    async def _get_idempotent_response(
        cls,
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        run_id: str,
        token_revision: int,
        idempotency_key: str,
    ) -> LoopRunDocument | None:
        """Return the response saved for an identical continuation request."""

        cursor = await connection.execute(
            '''
            SELECT response_json FROM loop_run_idempotency
            WHERE workspace_id = ? AND run_id = ? AND token_revision = ?
              AND idempotency_key = ?
            ''',
            (workspace_id, run_id, token_revision, idempotency_key),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        if row is None:
            return None
        return cls._document_from_json(json.loads(str(row['response_json'])))

    @staticmethod
    async def _get_checkpoint_revision(
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        run_id: str,
        continuation_token: str,
    ) -> int | None:
        """Return the revision that issued one continuation token."""

        cursor = await connection.execute(
            '''
            SELECT token_revision
            FROM loop_run_checkpoints
            WHERE workspace_id = ? AND run_id = ?
              AND continuation_token = ?
            ''',
            (workspace_id, run_id, continuation_token),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        return int(row['token_revision']) if row is not None else None

    @staticmethod
    async def _store_idempotent_response(
        connection: aiosqlite.Connection,
        *,
        workspace_id: str,
        run_id: str,
        token_revision: int,
        idempotency_key: str,
        document: LoopRunDocument,
        created_at: datetime,
    ) -> None:
        """Persist the exact response for safe continuation replay."""

        await connection.execute(
            '''
            INSERT INTO loop_run_idempotency (
                workspace_id, run_id, token_revision, idempotency_key,
                response_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                workspace_id,
                run_id,
                token_revision,
                idempotency_key,
                json.dumps(
                    SqliteLoopRunRepository._document_to_json(document),
                    sort_keys=True,
                ),
                SqliteLoopRunRepository._serialize_datetime(created_at),
            ),
        )

    @staticmethod
    def _document_to_json(document: LoopRunDocument) -> dict[str, object]:
        """Serialize a loop-run response for idempotency storage."""

        return {
            'id': document.id,
            'workspace_id': document.workspace_id,
            'loop_id': document.loop_id,
            'input': document.input,
            'status': document.status,
            'state': document.state,
            'next_action': document.next_action,
            'iteration': document.iteration,
            'token_revision': document.token_revision,
            'continuation_token': document.continuation_token,
            'loop_snapshot': dict(document.loop_snapshot),
            'execution_context': dict(document.execution_context),
            'created_at': SqliteLoopRunRepository._serialize_datetime(document.created_at),
            'created_by': document.created_by,
            'updated_at': SqliteLoopRunRepository._serialize_datetime(document.updated_at),
        }

    @staticmethod
    def _document_from_json(value: dict[str, object]) -> LoopRunDocument:
        """Restore one idempotency response into a loop-run document."""

        return LoopRunDocument(
            id=str(value['id']),
            workspace_id=str(value['workspace_id']),
            loop_id=str(value['loop_id']),
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
            loop_snapshot=dict(value['loop_snapshot']),
            execution_context=dict(value['execution_context']),
            created_at=datetime.fromisoformat(str(value['created_at'])),
            created_by=str(value['created_by']),
            updated_at=datetime.fromisoformat(str(value['updated_at'])),
        )

    @staticmethod
    def _serialize_datetime(value: datetime) -> str:
        """Serialize an aware datetime in SQLite's ISO representation."""

        return value.isoformat()

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
