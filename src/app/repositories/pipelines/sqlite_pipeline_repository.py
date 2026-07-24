"""SQLite persistence for pipelines and their changelog."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.app.models.pipeline import (
    PipelineChangelogEntry,
    PipelineDocument,
    PipelineStatus,
)
from src.app.repositories.pipelines.pipeline_repository_mapping import (
    count_pipelines,
    insert_changelog,
    insert_pipeline,
    insert_steps,
    list_filter,
    to_changelog_entry,
    to_document,
)


class SqlitePipelineRepository:
    """Persist pipeline aggregates and changelog entries in SQLite."""

    def __init__(self, database_path: str | Path) -> None:
        """Store the database path used for repository connections."""

        self._database_path = Path(database_path)

    async def list(
        self,
        *,
        workspace_id: str,
        offset: int,
        limit: int,
        status: PipelineStatus | None,
        search: str | None,
    ) -> tuple[list[PipelineDocument], int]:
        """Return one filtered page with active pipelines ordered first."""

        where, parameters = list_filter(
            workspace_id=workspace_id,
            status=status,
            search=search,
        )
        async with self._connect() as connection:
            total = await count_pipelines(connection, where, parameters)
            cursor = await connection.execute(
                f"""
                SELECT *
                FROM pipelines
                WHERE {where}
                ORDER BY
                    CASE status
                        WHEN 'active' THEN 0
                        WHEN 'disabled' THEN 1
                        ELSE 2
                    END,
                    updated_at DESC,
                    id ASC
                LIMIT ? OFFSET ?
                """,
                (*parameters, limit, offset),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
            documents = [
                await to_document(connection, row)
                for row in rows
            ]
        return documents, total

    async def get(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
    ) -> PipelineDocument | None:
        """Return one pipeline with its ordered steps."""

        async with self._connect() as connection:
            row = await self._get_row(
                connection,
                workspace_id,
                pipeline_id,
            )
            if row is None:
                return None
            return await to_document(connection, row)

    async def create(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> PipelineDocument:
        """Insert a pipeline and creation entry atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                await insert_pipeline(connection, document)
                await insert_steps(connection, document)
                await insert_changelog(connection, changelog_entry)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return document

    async def update(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> bool:
        """Replace mutable fields and append a changelog entry atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                updated = await self._update_row(connection, document)
                if not updated:
                    await connection.rollback()
                    return False
                await connection.execute(
                    """
                    DELETE FROM pipeline_steps
                    WHERE workspace_id = ? AND pipeline_id = ?
                    """,
                    (document.workspace_id, document.id),
                )
                await insert_steps(connection, document)
                await insert_changelog(connection, changelog_entry)
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def archive(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> bool:
        """Persist archival and its changelog entry atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                updated = await self._update_row(connection, document)
                if not updated:
                    await connection.rollback()
                    return False
                await insert_changelog(connection, changelog_entry)
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def list_changelog(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[PipelineChangelogEntry], int]:
        """Return pipeline changelog entries from newest to oldest."""

        async with self._connect() as connection:
            count_cursor = await connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM pipeline_changelog_entries
                WHERE workspace_id = ? AND pipeline_id = ?
                """,
                (workspace_id, pipeline_id),
            )
            try:
                count_row = await count_cursor.fetchone()
            finally:
                await count_cursor.close()
            total = int(count_row["total"]) if count_row is not None else 0

            cursor = await connection.execute(
                """
                SELECT *
                FROM pipeline_changelog_entries
                WHERE workspace_id = ? AND pipeline_id = ?
                ORDER BY changed_at DESC, rowid DESC
                LIMIT ? OFFSET ?
                """,
                (workspace_id, pipeline_id, limit, offset),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return [to_changelog_entry(row) for row in rows], total

    @staticmethod
    async def _update_row(
        connection: aiosqlite.Connection,
        document: PipelineDocument,
    ) -> bool:
        """Update scalar pipeline fields with an existing transaction."""

        cursor = await connection.execute(
            """
            UPDATE pipelines
            SET title = ?, description = ?, status = ?,
                updated_at = ?, updated_by = ?
            WHERE workspace_id = ? AND id = ?
            """,
            (
                document.title,
                document.description,
                document.status,
                document.updated_at.isoformat(),
                document.updated_by,
                document.workspace_id,
                document.id,
            ),
        )
        try:
            return cursor.rowcount == 1
        finally:
            await cursor.close()

    @staticmethod
    async def _get_row(
        connection: aiosqlite.Connection,
        workspace_id: str,
        pipeline_id: str,
    ) -> aiosqlite.Row | None:
        """Return one scalar pipeline row."""

        cursor = await connection.execute(
            "SELECT * FROM pipelines WHERE workspace_id = ? AND id = ?",
            (workspace_id, pipeline_id),
        )
        try:
            return await cursor.fetchone()
        finally:
            await cursor.close()

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Open one configured SQLite connection."""

        connection = await aiosqlite.connect(self._database_path)
        connection.row_factory = aiosqlite.Row
        try:
            await connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        finally:
            await connection.close()
