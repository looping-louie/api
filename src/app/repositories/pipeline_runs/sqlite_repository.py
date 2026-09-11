"""SQLite persistence for durable pipeline execution state."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline_run import (
    PipelineRunDocument,
    PipelineRunEventDocument,
    PipelineRunStepDocument,
)


class SqlitePipelineRunRepository:
    """Persist pipeline state with selected child activity runs atomically."""

    def __init__(self, database_path: str | Path) -> None:
        """Store the SQLite database path used for connections."""

        self._database_path = Path(database_path)

    async def list(
        self,
        *,
        project_id: str,
        offset: int,
        limit: int,
        created_from: datetime | None,
    ) -> tuple[list[PipelineRunDocument], int]:
        """Return newest filtered Pipeline runs within one Project."""

        clauses = ['project_id = ?']
        parameters: list[object] = [project_id]
        if created_from is not None:
            clauses.append('julianday(created_at) >= julianday(?)')
            parameters.append(created_from.isoformat())
        where = ' AND '.join(clauses)

        async with self._connect() as connection:
            count_cursor = await connection.execute(
                f'SELECT COUNT(*) FROM pipeline_runs WHERE {where}',
                parameters,
            )
            try:
                total = int((await count_cursor.fetchone())[0])
            finally:
                await count_cursor.close()
            cursor = await connection.execute(
                f'''
                SELECT * FROM pipeline_runs
                WHERE {where}
                ORDER BY created_at DESC, id ASC
                LIMIT ? OFFSET ?
                ''',
                (*parameters, limit, offset),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
            documents = [await self._to_document(connection, row) for row in rows]
        return documents, total

    async def create(
        self,
        *,
        document: PipelineRunDocument,
        activity_run: ActivityRunDocument | None,
    ) -> PipelineRunDocument:
        """Insert a run, its frozen steps, and its first child in one transaction."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await self._insert_run(connection, document)
                await self._insert_steps(connection, document)
                await self._insert_events(connection, document.events)
                if activity_run is not None:  # Only insert if activity_run is provided
                    await self._insert_activity_run(connection, activity_run)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return document

    async def get(
        self,
        *,
        project_id: str,
        pipeline_id: str,
        run_id: str,
    ) -> PipelineRunDocument | None:
        """Return one pipeline run and its frozen steps."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT * FROM pipeline_runs
                WHERE project_id = ? AND pipeline_id = ? AND id = ?
                ''',
                (project_id, pipeline_id, run_id),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            if row is None:
                return None
            return await self._to_document(connection, row)

    async def start(
        self,
        *,
        document: PipelineRunDocument,
        expected_updated_at: datetime,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Queue a prepared run or persist its ready human child atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                if activity_run is not None:
                    await self._insert_activity_run(connection, activity_run)
                cursor = await connection.execute(
                    '''
                    UPDATE pipeline_runs
                    SET status = ?, worker_id = ?, lease_token = ?,
                        lease_expires_at = ?, current_activity_run_id = ?,
                        updated_at = ?
                    WHERE project_id = ? AND pipeline_id = ? AND id = ?
                        AND updated_at = ? AND status = 'prepared'
                    ''',
                    (
                        document.status, document.worker_id, document.lease_token,
                        document.lease_expires_at.isoformat()
                        if document.lease_expires_at is not None else None,
                        document.current_activity_run_id,
                        document.updated_at.isoformat(), document.project_id,
                        document.pipeline_id, document.id,
                        expected_updated_at.isoformat(),
                    ),
                )
                try:
                    started = cursor.rowcount == 1
                finally:
                    await cursor.close()
                if not started:
                    await connection.rollback()
                    return False
                await self._update_steps(connection, document)
                await self._insert_events(connection, document.events)
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def list_claimable(
        self,
        *,
        project_id: str,
        pipeline_id: str,
        claimed_before: datetime,
    ) -> list[PipelineRunDocument]:
        """Return queued or expired claimed runs in one Pipeline."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT * FROM pipeline_runs
                WHERE project_id = ? AND pipeline_id = ?
                  AND (
                    status = 'queued'
                    OR (status = 'claimed' AND lease_expires_at <= ?)
                  )
                ORDER BY created_at ASC
                ''',
                (project_id, pipeline_id, claimed_before.isoformat()),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
            return [await self._to_document(connection, row) for row in rows]

    async def list_events(
        self,
        *,
        project_id: str,
        pipeline_id: str,
        run_id: str,
    ) -> list[PipelineRunEventDocument]:
        """Return immutable events from one scoped Pipeline execution."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT events.*
                FROM pipeline_run_events AS events
                JOIN pipeline_runs AS runs
                    ON runs.project_id = events.project_id
                    AND runs.id = events.pipeline_run_id
                WHERE events.project_id = ?
                    AND events.pipeline_run_id = ?
                    AND runs.pipeline_id = ?
                ORDER BY events.created_at ASC, events.id ASC
                ''',
                (project_id, run_id, pipeline_id),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return [self._to_event(row) for row in rows]

    async def claim(
        self,
        *,
        document: PipelineRunDocument,
        expected_updated_at: datetime,
        expected_current_activity_run_id: str | None,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Assign a claim only while its observed queue state remains current."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                if activity_run is not None:
                    await self._insert_activity_run(connection, activity_run)
                cursor = await connection.execute(
                    '''
                    UPDATE pipeline_runs
                    SET status = ?, worker_id = ?, lease_token = ?,
                        lease_expires_at = ?, attempt = ?,
                        current_activity_run_id = ?, updated_at = ?
                    WHERE project_id = ? AND pipeline_id = ? AND id = ?
                      AND updated_at = ? AND current_activity_run_id IS ?
                      AND status IN ('queued', 'claimed')
                    ''',
                    (
                        document.status, document.worker_id, document.lease_token,
                        document.lease_expires_at.isoformat()
                        if document.lease_expires_at is not None else None,
                        document.attempt, document.current_activity_run_id,
                        document.updated_at.isoformat(), document.project_id,
                        document.pipeline_id, document.id,
                        expected_updated_at.isoformat(),
                        expected_current_activity_run_id,
                    ),
                )
                try:
                    claimed = cursor.rowcount == 1
                finally:
                    await cursor.close()
                if not claimed:
                    await connection.rollback()
                    return False
                await self._update_steps(connection, document)
                await self._insert_events(connection, document.events)
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def renew_lease(
        self,
        *,
        document: PipelineRunDocument,
        expected_lease_token: str | None,
        now: datetime,
    ) -> bool:
        """Extend an unexpired lease only while its worker token remains current."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                '''
                UPDATE pipeline_runs
                SET lease_expires_at = ?, updated_at = ?
                WHERE project_id = ? AND pipeline_id = ? AND id = ?
                  AND lease_token = ? AND lease_expires_at > ?
                  AND status IN ('claimed', 'in_progress')
                ''',
                (
                    document.lease_expires_at.isoformat()
                    if document.lease_expires_at is not None else None,
                    document.updated_at.isoformat(), document.project_id,
                    document.pipeline_id, document.id, expected_lease_token,
                    now.isoformat(),
                ),
            )
            try:
                renewed = cursor.rowcount == 1
            finally:
                await cursor.close()
            await connection.commit()
            return renewed

    async def transition(
        self,
        *,
        document: PipelineRunDocument,
        expected_current_activity_run_id: str | None,
        expected_lease_token: str,
        now: datetime,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Replace state only when no other scheduler changed its current child."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                if activity_run is not None:
                    await self._insert_activity_run(connection, activity_run)
                cursor = await connection.execute(
                    '''
                    UPDATE pipeline_runs
                    SET status = ?, worker_id = ?, lease_token = ?,
                        lease_expires_at = ?, current_activity_run_id = ?,
                        updated_at = ?
                    WHERE project_id = ? AND pipeline_id = ? AND id = ?
                      AND current_activity_run_id IS ?
                      AND (
                            (lease_token = ? AND lease_expires_at > ?
                                AND status IN ('claimed', 'in_progress'))
                            OR (status = 'waiting' AND lease_token IS NULL AND ? IS NULL)
                      )
                    ''',
                    (
                        document.status,
                        document.worker_id,
                        document.lease_token,
                        document.lease_expires_at.isoformat()
                        if document.lease_expires_at is not None else None,
                        document.current_activity_run_id,
                        document.updated_at.isoformat(),
                        document.project_id,
                        document.pipeline_id,
                        document.id,
                        expected_current_activity_run_id,
                        expected_lease_token,
                        now.isoformat(),
                        expected_lease_token,
                    ),
                )
                try:
                    updated = cursor.rowcount == 1
                finally:
                    await cursor.close()
                if not updated:
                    await connection.rollback()
                    return False
                await self._update_steps(connection, document)
                await self._insert_events(connection, document.events)
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Open a row-mapped SQLite connection for one repository operation."""

        connection = await aiosqlite.connect(self._database_path)
        connection.row_factory = aiosqlite.Row
        try:
            yield connection
        finally:
            await connection.close()

    @staticmethod
    async def _insert_run(
        connection: aiosqlite.Connection,
        document: PipelineRunDocument,
    ) -> None:
        """Insert one pipeline-run scalar record."""

        await connection.execute(
            '''
            INSERT INTO pipeline_runs (
                id, project_id, pipeline_id, input, commit_mode, status,
                worker_id, lease_token, lease_expires_at, attempt,
                current_activity_run_id, pipeline_snapshot_json,
                created_at, created_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                document.id, document.project_id, document.pipeline_id,
                document.input, document.commit_mode, document.status, document.worker_id,
                document.lease_token,
                document.lease_expires_at.isoformat()
                if document.lease_expires_at is not None else None,
                document.attempt, document.current_activity_run_id,
                json.dumps(document.pipeline_snapshot, sort_keys=True),
                document.created_at.isoformat(), document.created_by,
                document.updated_at.isoformat(),
            ),
        )

    @staticmethod
    async def _insert_steps(
        connection: aiosqlite.Connection,
        document: PipelineRunDocument,
    ) -> None:
        """Insert every frozen step in pipeline display order."""

        await connection.executemany(
            '''
            INSERT INTO pipeline_run_steps (
                project_id, pipeline_run_id, position, activity_id, status,
                activity_run_id, activity_snapshot_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            [
                (
                    document.project_id, document.id, step.position,
                    step.activity_id, step.status, step.activity_run_id,
                    json.dumps(step.activity_snapshot, sort_keys=True),
                    step.updated_at.isoformat(),
                )
                for step in document.steps
            ],
        )

    @staticmethod
    async def _update_steps(
        connection: aiosqlite.Connection,
        document: PipelineRunDocument,
    ) -> None:
        """Update mutable scheduler fields for every frozen step."""

        await connection.executemany(
            '''
            UPDATE pipeline_run_steps
            SET status = ?, activity_run_id = ?, updated_at = ?
            WHERE project_id = ? AND pipeline_run_id = ? AND position = ?
            ''',
            [
                (
                    step.status, step.activity_run_id, step.updated_at.isoformat(),
                    document.project_id, document.id, step.position,
                )
                for step in document.steps
            ],
        )

    @staticmethod
    async def _insert_events(
        connection: aiosqlite.Connection,
        events: tuple[PipelineRunEventDocument, ...],
    ) -> None:
        """Append supplied immutable Pipeline-run events."""

        await connection.executemany(
            '''
            INSERT INTO pipeline_run_events (
                id, project_id, pipeline_run_id, event_type, activity_id,
                actor_id, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            [
                (
                    event.id,
                    event.project_id,
                    event.pipeline_run_id,
                    event.event_type,
                    event.activity_id,
                    event.actor_id,
                    json.dumps(event.payload, sort_keys=True),
                    event.created_at.isoformat(),
                )
                for event in events
            ],
        )

    @staticmethod
    async def _insert_activity_run(
        connection: aiosqlite.Connection,
        document: ActivityRunDocument,
    ) -> None:
        """Create the selected child run and its initial checkpoint atomically."""

        await connection.execute(
            '''
            INSERT INTO activity_runs (
                id, project_id, activity_id, input, status, state, next_action,
                iteration, token_revision, continuation_token, activity_snapshot_json,
                execution_context_json, created_at, created_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                document.id, document.project_id, document.activity_id,
                document.input, document.status, document.state,
                document.next_action, document.iteration, document.token_revision,
                document.continuation_token,
                json.dumps(document.activity_snapshot, sort_keys=True),
                json.dumps(document.execution_context, sort_keys=True),
                document.created_at.isoformat(), document.created_by,
                document.updated_at.isoformat(),
            ),
        )
        await connection.execute(
            '''
            INSERT INTO activity_run_checkpoints (
                project_id, run_id, token_revision, continuation_token,
                state, next_action, context_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                document.project_id, document.id, document.token_revision,
                document.continuation_token, document.state, document.next_action,
                json.dumps(document.execution_context, sort_keys=True),
                document.created_at.isoformat(),
            ),
        )

    @classmethod
    async def _to_document(
        cls,
        connection: aiosqlite.Connection,
        row: aiosqlite.Row,
    ) -> PipelineRunDocument:
        """Map one persisted run and its steps into the domain representation."""

        cursor = await connection.execute(
            '''
            SELECT * FROM pipeline_run_steps
            WHERE project_id = ? AND pipeline_run_id = ?
            ORDER BY position ASC
            ''',
            (row['project_id'], row['id']),
        )
        try:
            step_rows = await cursor.fetchall()
        finally:
            await cursor.close()
        return PipelineRunDocument(
            id=str(row['id']), project_id=str(row['project_id']),
            pipeline_id=str(row['pipeline_id']), input=str(row['input']),
            commit_mode=row['commit_mode'],
            status=row['status'], worker_id=row['worker_id'],
            lease_token=row['lease_token'],
            lease_expires_at=(
                datetime.fromisoformat(str(row['lease_expires_at']))
                if row['lease_expires_at'] is not None else None
            ),
            attempt=int(row['attempt']),
            current_activity_run_id=row['current_activity_run_id'],
            pipeline_snapshot=json.loads(str(row['pipeline_snapshot_json'])),
            steps=tuple(cls._to_step(step_row) for step_row in step_rows),
            created_at=datetime.fromisoformat(str(row['created_at'])),
            created_by=str(row['created_by']),
            updated_at=datetime.fromisoformat(str(row['updated_at'])),
        )

    @staticmethod
    def _to_event(row: aiosqlite.Row) -> PipelineRunEventDocument:
        """Map one immutable persisted Pipeline-run event."""

        return PipelineRunEventDocument(
            id=str(row['id']),
            project_id=str(row['project_id']),
            pipeline_run_id=str(row['pipeline_run_id']),
            event_type=str(row['event_type']),
            activity_id=row['activity_id'],
            actor_id=str(row['actor_id']),
            payload=json.loads(str(row['payload_json'])),
            created_at=datetime.fromisoformat(str(row['created_at'])),
        )


    @staticmethod
    def _to_step(row: aiosqlite.Row) -> PipelineRunStepDocument:
        """Map one persisted pipeline step into its domain representation."""

        return PipelineRunStepDocument(
            position=int(row['position']), activity_id=str(row['activity_id']),
            status=row['status'], activity_run_id=row['activity_run_id'],
            activity_snapshot=json.loads(str(row['activity_snapshot_json'])),
            updated_at=datetime.fromisoformat(str(row['updated_at'])),
        )
