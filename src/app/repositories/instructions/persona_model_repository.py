"""SQLite persistence for optional persona-model associations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


class SqlitePersonaModelRepository:
    """Persist one optional model identifier for each persona."""

    def __init__(self, database_path: str | Path) -> None:
        """Initialize the repository for one SQLite database."""

        self._database_path = Path(database_path)

    async def get_for_persona(self, *, persona_id: str) -> str | None:
        """Return the stored model identifier when one exists."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                "SELECT model_id FROM persona_models WHERE persona_id = ?",
                (persona_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()

        return str(row['model_id']) if row is not None else None

    async def replace_for_persona(
        self,
        *,
        persona_id: str,
        model_id: str | None,
    ) -> None:
        """Store or remove the optional model association."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    'DELETE FROM persona_models WHERE persona_id = ?',
                    (persona_id,),
                )
                if model_id is not None:
                    await connection.execute(
                        'INSERT INTO persona_models (persona_id, model_id) VALUES (?, ?)',
                        (persona_id, model_id),
                    )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Open a connection with referential integrity enabled."""

        connection = await aiosqlite.connect(self._database_path)
        try:
            connection.row_factory = aiosqlite.Row
            await connection.execute('PRAGMA foreign_keys = ON')
            yield connection
        finally:
            await connection.close()
