"""SQLite persistence for activities and their changelog."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.app.models.activity import ActivityChangelogEntry, ActivityDocument
from src.app.models.pipeline import PipelineHarness


class SqliteActivityRepository:
    """Persist activity aggregates and changelog entries in SQLite."""

    def __init__(self, database_path: str | Path) -> None:
        """Store the database path used for repository connections."""

        self._database_path = Path(database_path)

    async def list(self, *, user_id: str, offset: int, limit: int) -> tuple[list[ActivityDocument], int]:
        """Return one user's Activities ordered by most recent update."""

        async with self._connect() as connection:
            total = await self._count(connection, user_id)
            cursor = await connection.execute(
                'SELECT * FROM activities WHERE user_id = ? '
                'ORDER BY updated_at DESC, id ASC LIMIT ? OFFSET ?',
                (user_id, limit, offset),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return [self._document(row) for row in rows], total

    async def get(self, *, user_id: str, activity_id: str) -> ActivityDocument | None:
        """Return one Activity owned by the requested user."""

        async with self._connect() as connection:
            row = await self._get_row(connection, user_id, activity_id)
        return self._document(row) if row is not None else None

    async def create(self, *, document: ActivityDocument, changelog_entry: ActivityChangelogEntry) -> ActivityDocument:
        """Insert an activity and creation entry in one transaction."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await self._insert_document(connection, document)
                await self._insert_entry(connection, changelog_entry)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return document

    async def update(self, *, document: ActivityDocument, changelog_entry: ActivityChangelogEntry) -> bool:
        """Replace an activity and append its entry atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                cursor = await connection.execute(
                    'UPDATE activities SET name = ?, description = ?, status = ?, '
                    'activity_type = ?, config_json = ?, model_id = ?, '
                    'harness_json = ?, updated_at = ?, updated_by = ? '
                    'WHERE user_id = ? AND id = ?',
                    self._update_values(document),
                )
                try:
                    updated = cursor.rowcount == 1
                finally:
                    await cursor.close()
                if not updated:
                    await connection.rollback()
                    return False
                await self._insert_entry(connection, changelog_entry)
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def delete(self, *, user_id: str, activity_id: str, changelog_entry: ActivityChangelogEntry) -> bool:
        """Append a deletion entry before deleting the activity atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                if await self._get_row(connection, user_id, activity_id) is None:
                    await connection.rollback()
                    return False
                await self._insert_entry(connection, changelog_entry)
                await connection.execute(
                    'DELETE FROM activities WHERE user_id = ? AND id = ?',
                    (user_id, activity_id),
                )
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def list_changelog(self, *, user_id: str, activity_id: str, offset: int, limit: int) -> tuple[list[ActivityChangelogEntry], int]:
        """Return changelog entries ordered from newest to oldest."""

        async with self._connect() as connection:
            count_cursor = await connection.execute(
                'SELECT COUNT(*) AS total FROM activity_changelog_entries '
                'WHERE user_id = ? AND activity_id = ?',
                (user_id, activity_id),
            )
            try:
                count_row = await count_cursor.fetchone()
            finally:
                await count_cursor.close()
            cursor = await connection.execute(
                'SELECT * FROM activity_changelog_entries WHERE user_id = ? '
                'AND activity_id = ? ORDER BY changed_at DESC, rowid DESC LIMIT ? OFFSET ?',
                (user_id, activity_id, limit, offset),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        total = int(count_row['total']) if count_row is not None else 0
        return [self._entry(row) for row in rows], total

    @staticmethod
    def _document(row: aiosqlite.Row) -> ActivityDocument:
        """Map one activity row to its domain document."""

        return ActivityDocument(
            id=row['id'], user_id=row['user_id'], name=row['name'],
            description=row['description'], status=row['status'], type=row['activity_type'],
            config=json.loads(row['config_json']), created_at=datetime.fromisoformat(row['created_at']),
            created_by=row['created_by'], updated_at=datetime.fromisoformat(row['updated_at']),
            updated_by=row['updated_by'],
            model_id=row['model_id'],
            harness=_harness(row['harness_json']),
        )

    @staticmethod
    def _entry(row: aiosqlite.Row) -> ActivityChangelogEntry:
        """Map one changelog row to its domain entry."""

        return ActivityChangelogEntry(
            id=row['id'], activity_id=row['activity_id'], user_id=row['user_id'],
            change_type=row['change_type'], actor_id=row['actor_id'],
            changed_at=datetime.fromisoformat(row['changed_at']),
            diff=json.loads(row['diff_json']) if row['diff_json'] else None,
            content=json.loads(row['content_json']) if row['content_json'] else None,
        )

    @staticmethod
    async def _get_row(connection: aiosqlite.Connection, user_id: str, activity_id: str) -> aiosqlite.Row | None:
        """Return one activity row using an existing connection."""

        cursor = await connection.execute(
            'SELECT * FROM activities WHERE user_id = ? AND id = ?',
            (user_id, activity_id),
        )
        try:
            return await cursor.fetchone()
        finally:
            await cursor.close()

    @staticmethod
    async def _count(connection: aiosqlite.Connection, user_id: str) -> int:
        """Count Activities owned by one User."""

        cursor = await connection.execute('SELECT COUNT(*) AS total FROM activities WHERE user_id = ?', (user_id,))
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        return int(row['total']) if row is not None else 0

    @staticmethod
    async def _insert_document(connection: aiosqlite.Connection, document: ActivityDocument) -> None:
        """Insert one activity document."""

        await connection.execute(
            'INSERT INTO activities (id, user_id, workspace_id, name, description, status, '
            'activity_type, config_json, model_id, harness_json, created_at, '
            'created_by, updated_at, updated_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                document.id, document.user_id, None, document.name, document.description,
                document.status, document.type, json.dumps(document.config),
                document.model_id, _harness_json(document.harness),
                document.created_at.isoformat(), document.created_by, document.updated_at.isoformat(),
                document.updated_by,
            ),
        )

    @staticmethod
    async def _insert_entry(connection: aiosqlite.Connection, entry: ActivityChangelogEntry) -> None:
        """Insert one immutable activity changelog entry."""

        await connection.execute(
            'INSERT INTO activity_changelog_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                entry.id, entry.activity_id, entry.user_id, None, entry.change_type,
                entry.actor_id, entry.changed_at.isoformat(),
                json.dumps(entry.diff) if entry.diff is not None else None,
                json.dumps(entry.content) if entry.content is not None else None,
            ),
        )

    @staticmethod
    def _update_values(document: ActivityDocument) -> tuple[object, ...]:
        """Return values for the activity update statement."""

        return (
            document.name, document.description, document.status, document.type,
            json.dumps(document.config), document.model_id,
            _harness_json(document.harness), document.updated_at.isoformat(), document.updated_by,
            document.user_id, document.id,
        )

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Open one configured SQLite connection."""

        connection = await aiosqlite.connect(self._database_path)
        connection.row_factory = aiosqlite.Row
        try:
            await connection.execute('PRAGMA foreign_keys = ON')
            yield connection
        finally:
            await connection.close()


def _harness(value: str | None) -> PipelineHarness | None:
    """Deserialize one optional activity Harness."""

    if value is None:
        return None
    parsed = json.loads(value)
    return PipelineHarness(
        kind=parsed['kind'],
        version=parsed['version'],
        config=parsed['config'],
    )


def _harness_json(harness: PipelineHarness | None) -> str | None:
    """Serialize an optional activity Harness."""

    if harness is None:
        return None
    return json.dumps({
        'kind': harness.kind,
        'version': harness.version,
        'config': dict(harness.config),
    })
