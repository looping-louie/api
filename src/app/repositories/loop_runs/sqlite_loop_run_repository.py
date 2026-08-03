"""SQLite persistence for loop execution records."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.app.models.loop_run import LoopRunDocument


class SqliteLoopRunRepository:
    """Persist loop runs independently from pipeline execution state."""

    def __init__(self, database_path: str | Path) -> None:
        """Store the SQLite database path used for connections."""

        self._database_path = Path(database_path)

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
                        loop_snapshot_json, created_at, created_by, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        json.dumps(document.loop_snapshot, sort_keys=True),
                        self._serialize_datetime(document.created_at),
                        document.created_by,
                        self._serialize_datetime(document.updated_at),
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

    @staticmethod
    def _to_document(row: aiosqlite.Row) -> LoopRunDocument:
        """Map one persisted loop-run row into its domain representation."""

        return LoopRunDocument(
            id=str(row['id']),
            workspace_id=str(row['workspace_id']),
            loop_id=str(row['loop_id']),
            input=str(row['input']),
            status=str(row['status']),
            state=str(row['state']),
            next_action=str(row['next_action']),
            iteration=int(row['iteration']),
            token_revision=int(row['token_revision']),
            loop_snapshot=json.loads(str(row['loop_snapshot_json'])),
            created_at=datetime.fromisoformat(str(row['created_at'])),
            created_by=str(row['created_by']),
            updated_at=datetime.fromisoformat(str(row['updated_at'])),
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