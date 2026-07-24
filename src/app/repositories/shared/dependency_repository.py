"""SQLite dependency lookup adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.app.services.shared.dependency_checker import DependencyUsage
from src.app.services.shared.reference_resolver import ResourceReference


class SqliteDependencyRepository:
    """Read loop-to-persona dependencies from SQLite."""

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        """Store the SQLite database path."""

        self._database_path = Path(database_path)

    async def find_usages(
        self,
        *,
        workspace_id: str,
        target: ResourceReference
    ) -> list[DependencyUsage]:
        """Return resources currently referencing the target."""

        if target.resource_type != "persona":
            return []

        async with self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT DISTINCT loop_id
                FROM loop_agents
                WHERE workspace_id = ? AND persona_id = ?
                ORDER BY loop_id ASC
                """,
                (workspace_id, target.resource_id),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return [
            DependencyUsage(
                source=ResourceReference(
                    resource_type="loop",
                    resource_id=str(row["loop_id"]),
                ),
                relation="persona",
            )
            for row in rows
        ]

    @asynccontextmanager
    async def _connect(
        self,
    ) -> AsyncIterator[aiosqlite.Connection]:
        """Open one configured read connection."""

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
