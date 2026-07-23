"""SQLite dependency lookup adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.app.services.shared.dependency_checker import DependencyUsage
from src.app.services.shared.reference_resolver import ResourceReference


class SqliteDependencyRepository:
    """Reads workspace-scoped composition dependencies from SQLite.

    ``workspace_id`` belongs to the referencing composition, not necessarily
    to the target. This lets several workspaces safely reference the same
    global builtin instruction ID while custom deletion remains isolated to
    its owning workspace.
    """

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self._database_path = Path(database_path)

    async def find_usages(
        self,
        *,
        workspace_id: str,
        target: ResourceReference
    ) -> list[DependencyUsage]:
        """Return resources currently referencing the target."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT DISTINCT
                    source_type,
                    source_id,
                    relation
                FROM resource_dependencies
                WHERE workspace_id = ?
                  AND target_type = ?
                  AND target_id = ?
                ORDER BY
                    source_type ASC,
                    source_id ASC,
                    relation ASC
                """,
                (
                    workspace_id,
                    target.resource_type,
                    target.resource_id,
                ),
            )

            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return [
            DependencyUsage(
                source=ResourceReference(
                    resource_type=str(row["source_type"]),
                    resource_id=str(row["source_id"]),
                ),
                relation=str(row["relation"]),
            )
            for row in rows
        ]

    @asynccontextmanager
    async def _connect(
        self,
    ) -> AsyncIterator[aiosqlite.Connection]:
        connection = await aiosqlite.connect(
            self._database_path,
        )

        try:
            connection.row_factory = aiosqlite.Row
            await connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            yield connection
        finally:
            await connection.close()
