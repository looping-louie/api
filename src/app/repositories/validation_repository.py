"""SQLite name lookup adapter for shared validation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


_RESOURCE_LOCATIONS: dict[str, tuple[str, str]] = {
    "persona": (
        "instructions",
        "instruction_type",
    ),
    "skill": (
        "instructions",
        "instruction_type",
    ),
    "council": (
        "compositions",
        "composition_type",
    ),
    "loop": (
        "compositions",
        "composition_type",
    ),
}


class SqliteValidationRepository:
    """Looks up resources by normalized name across shared tables."""

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self._database_path = Path(database_path)

    async def find_resource_id_by_name(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        normalized_name: str,
    ) -> str | None:
        """Return the resource with a matching normalized name."""

        location = _RESOURCE_LOCATIONS.get(resource_type)

        if location is None:
            raise ValueError(
                f"Unsupported resource type '{resource_type}'."
            )

        table_name, type_column = location
        name_key = normalized_name

        query = f"""
            SELECT id
            FROM {table_name}
            WHERE workspace_id = ?
              AND {type_column} = ?
              AND name_key = ?
            LIMIT 1
        """

        async with self._connect() as connection:
            cursor = await connection.execute(
                query,
                (
                    workspace_id,
                    resource_type,
                    name_key,
                ),
            )

            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()

        if row is None:
            return None

        return str(row["id"])

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

    @staticmethod
    def _normalize_name(name: str) -> str:
        return " ".join(
            name.strip().casefold().split()
        )
