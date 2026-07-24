"""SQLite persistence for loops and their changelog."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.app.models.loop import LoopChangelogEntry, LoopDocument
from .loop_repository_mapping import (
    insert_agents,
    insert_changelog,
    insert_loop,
    loop_update_values,
    to_changelog_entry,
    to_document,
)


class SqliteLoopRepository:
    """Persist loop aggregates and changelog entries in SQLite."""

    def __init__(self, database_path: str | Path) -> None:
        """Store the database path used for repository connections."""

        self._database_path = Path(database_path)

    async def list(
        self,
        *,
        workspace_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[LoopDocument], int]:
        """Return one page of loops ordered by most recent update."""

        async with self._connect() as connection:
            total = await self._count_loops(connection, workspace_id)
            cursor = await connection.execute(
                """
                SELECT *
                FROM loops
                WHERE workspace_id = ?
                ORDER BY updated_at DESC, id ASC
                LIMIT ? OFFSET ?
                """,
                (workspace_id, limit, offset),
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
        loop_id: str,
    ) -> LoopDocument | None:
        """Return one loop and its ordered agents."""

        async with self._connect() as connection:
            row = await self._get_row(connection, workspace_id, loop_id)
            if row is None:
                return None
            return await to_document(connection, row)

    async def create(
        self,
        *,
        document: LoopDocument,
        changelog_entry: LoopChangelogEntry,
    ) -> LoopDocument:
        """Insert a loop, agents, and creation entry in one transaction."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                await insert_loop(connection, document)
                await insert_agents(connection, document)
                await insert_changelog(connection, changelog_entry)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return document

    async def update(
        self,
        *,
        document: LoopDocument,
        changelog_entry: LoopChangelogEntry,
    ) -> bool:
        """Replace a loop and append its update entry atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                cursor = await connection.execute(
                    """
                    UPDATE loops
                    SET title = ?, description = ?, flow = ?, status = ?,
                        stop_conditions_json = ?, output_contract_json = ?,
                        updated_at = ?, updated_by = ?
                    WHERE workspace_id = ? AND id = ?
                    """,
                    loop_update_values(document),
                )
                try:
                    updated = cursor.rowcount == 1
                finally:
                    await cursor.close()
                if not updated:
                    await connection.rollback()
                    return False

                await connection.execute(
                    """
                    DELETE FROM loop_agents
                    WHERE workspace_id = ? AND loop_id = ?
                    """,
                    (document.workspace_id, document.id),
                )
                await insert_agents(connection, document)
                await insert_changelog(connection, changelog_entry)
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def delete(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        changelog_entry: LoopChangelogEntry,
    ) -> bool:
        """Append a deletion entry before deleting the loop atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                exists = await self._get_row(connection, workspace_id, loop_id)
                if exists is None:
                    await connection.rollback()
                    return False

                await insert_changelog(connection, changelog_entry)
                await connection.execute(
                    "DELETE FROM loops WHERE workspace_id = ? AND id = ?",
                    (workspace_id, loop_id),
                )
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def list_changelog(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[LoopChangelogEntry], int]:
        """Return changelog entries ordered from newest to oldest."""

        async with self._connect() as connection:
            count_cursor = await connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM loop_changelog_entries
                WHERE workspace_id = ? AND loop_id = ?
                """,
                (workspace_id, loop_id),
            )
            try:
                count_row = await count_cursor.fetchone()
            finally:
                await count_cursor.close()
            total = int(count_row["total"]) if count_row is not None else 0

            cursor = await connection.execute(
                """
                SELECT *
                FROM loop_changelog_entries
                WHERE workspace_id = ? AND loop_id = ?
                ORDER BY changed_at DESC, rowid DESC
                LIMIT ? OFFSET ?
                """,
                (workspace_id, loop_id, limit, offset),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return [to_changelog_entry(row) for row in rows], total

    @staticmethod
    async def _get_row(
        connection: aiosqlite.Connection,
        workspace_id: str,
        loop_id: str,
    ) -> aiosqlite.Row | None:
        """Return one scalar loop row using an existing connection."""

        cursor = await connection.execute(
            "SELECT * FROM loops WHERE workspace_id = ? AND id = ?",
            (workspace_id, loop_id),
        )
        try:
            return await cursor.fetchone()
        finally:
            await cursor.close()

    @staticmethod
    async def _count_loops(
        connection: aiosqlite.Connection,
        workspace_id: str,
    ) -> int:
        """Count loops in one workspace."""

        cursor = await connection.execute(
            "SELECT COUNT(*) AS total FROM loops WHERE workspace_id = ?",
            (workspace_id,),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        return int(row["total"]) if row is not None else 0

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
