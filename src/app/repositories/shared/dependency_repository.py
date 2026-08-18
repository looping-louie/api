"""SQLite dependency lookup adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.app.services.shared.dependency_checker import DependencyUsage
from src.app.services.shared.reference_resolver import ResourceReference


class SqliteDependencyRepository:
    """Read resource dependencies from SQLite."""

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

        if target.resource_type == "activity":
            return await self._find_pipeline_usages(
                workspace_id=workspace_id,
            activity_id=target.resource_id,
            )
        if target.resource_type == "persona":
            return await self._find_loop_usages(
                workspace_id=workspace_id,
                persona_id=target.resource_id,
            )
        if target.resource_type == 'linked_service':
            return await self._find_persona_usages(
                workspace_id=workspace_id,
                linked_service_id=target.resource_id,
            )
        return []

    async def _find_persona_usages(
        self,
        *,
        workspace_id: str,
        linked_service_id: str,
    ) -> list[DependencyUsage]:
        """Return personas selecting one linked service."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT selections.persona_id
                FROM persona_linked_service_selections AS selections
                JOIN instructions
                    ON instructions.id = selections.persona_id
                WHERE instructions.owner_workspace_id = ?
                    AND selections.linked_service_id = ?
                ORDER BY selections.persona_id ASC
                ''',
                (workspace_id, linked_service_id),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return [
            DependencyUsage(
                source=ResourceReference(
                    resource_type='persona',
                    resource_id=str(row['persona_id']),
                ),
                relation='linked_service',
            )
            for row in rows
        ]

    async def _find_loop_usages(
        self,
        *,
        workspace_id: str,
        persona_id: str,
    ) -> list[DependencyUsage]:
        """Return loops assigning one persona."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT DISTINCT loop_agents.loop_id, loops.status
                FROM loop_agents
                JOIN loops
                    ON loops.workspace_id = loop_agents.workspace_id
                    AND loops.id = loop_agents.loop_id
                WHERE loop_agents.workspace_id = ?
                    AND loop_agents.persona_id = ?
                ORDER BY loop_agents.loop_id ASC
                """,
                (workspace_id, persona_id),
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
                blocking=str(row["status"]) != "archived",
            )
            for row in rows
        ]

    async def _find_pipeline_usages(
        self,
        *,
        workspace_id: str,
        activity_id: str,
    ) -> list[DependencyUsage]:
        """Return pipelines containing one activity reference."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT DISTINCT pipeline_id
                FROM pipeline_steps
                WHERE workspace_id = ? AND activity_id = ?
                ORDER BY pipeline_id ASC
                """,
                (workspace_id, activity_id),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return [
            DependencyUsage(
                source=ResourceReference(
                    resource_type="pipeline",
                    resource_id=str(row["pipeline_id"]),
                ),
                relation="activity",
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
