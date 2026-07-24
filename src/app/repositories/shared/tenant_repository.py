"""SQLite persistence for workspace memberships."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import aiosqlite

from src.app.services.shared.tenant_service import WorkspaceMembership


class SqliteTenantRepository:
    """Reads workspace memberships from SQLite."""

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        """Store the SQLite database path."""

        self._database_path = Path(database_path)

    async def get_membership(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceMembership | None:
        """Return one membership for a user and workspace."""

        row = await self._fetch_one(
            """
            SELECT
                user_id,
                workspace_id,
                is_default
            FROM workspace_memberships
            WHERE user_id = ?
              AND workspace_id = ?
            LIMIT 1
            """,
            (
                user_id,
                workspace_id,
            ),
        )

        if row is None:
            return None

        return self._to_membership(row)

    async def get_default_membership(
        self,
        *,
        user_id: str,
    ) -> WorkspaceMembership | None:
        """Return the user's default workspace membership."""

        row = await self._fetch_one(
            """
            SELECT
                user_id,
                workspace_id,
                is_default
            FROM workspace_memberships
            WHERE user_id = ?
              AND is_default = 1
            LIMIT 1
            """,
            (user_id,),
        )

        if row is None:
            return None

        return self._to_membership(row)

    async def list_memberships(
        self,
        *,
        user_id: str,
    ) -> list[WorkspaceMembership]:
        """Return every workspace membership belonging to a user."""

        rows = await self._fetch_all(
            """
            SELECT
                user_id,
                workspace_id,
                is_default
            FROM workspace_memberships
            WHERE user_id = ?
            ORDER BY
                is_default DESC,
                created_at ASC,
                workspace_id ASC
            """,
            (user_id,),
        )

        return [
            self._to_membership(row)
            for row in rows
        ]

    async def _fetch_one(
        self,
        query: str,
        parameters: Sequence[Any],
    ) -> aiosqlite.Row | None:
        """Execute a query and return its first row."""

        async with aiosqlite.connect(
            self._database_path,
        ) as connection:
            connection.row_factory = aiosqlite.Row
            await connection.execute("PRAGMA foreign_keys = ON")

            cursor = await connection.execute(
                query,
                parameters,
            )

            try:
                return await cursor.fetchone()
            finally:
                await cursor.close()

    async def _fetch_all(
        self,
        query: str,
        parameters: Sequence[Any],
    ) -> list[aiosqlite.Row]:
        """Execute a query and return all rows."""

        async with aiosqlite.connect(
            self._database_path,
        ) as connection:
            connection.row_factory = aiosqlite.Row
            await connection.execute("PRAGMA foreign_keys = ON")

            cursor = await connection.execute(
                query,
                parameters,
            )

            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return list(rows)

    @staticmethod
    def _to_membership(
        row: aiosqlite.Row,
    ) -> WorkspaceMembership:
        """Convert a SQLite row into a workspace membership."""

        return WorkspaceMembership(
            user_id=str(row["user_id"]),
            workspace_id=str(row["workspace_id"]),
            is_default=bool(row["is_default"]),
        )
