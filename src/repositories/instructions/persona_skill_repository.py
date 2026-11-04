"""SQLite persistence for persona-skill associations."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


class SqlitePersonaSkillRepository:
    """Persist ordered skill associations independently of persona content."""

    def __init__(self, database_path: str | Path) -> None:
        """Initialize the repository for one SQLite database."""

        self._database_path = Path(database_path)

    async def list_for_persona(self, *, persona_id: str) -> tuple[str, ...]:
        """Return associated skill IDs in their declared order."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT skill_id
                FROM persona_skills
                WHERE persona_id = ?
                ORDER BY position ASC
                """,
                (persona_id,),
            )

            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return tuple(str(row["skill_id"]) for row in rows)

    async def replace_for_persona(
        self,
        *,
        persona_id: str,
        skill_ids: Sequence[str],
    ) -> None:
        """Replace all associations for a persona atomically."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                await connection.execute(
                    "DELETE FROM persona_skills WHERE persona_id = ?",
                    (persona_id,),
                )

                if skill_ids:
                    await connection.executemany(
                        """
                        INSERT INTO persona_skills (
                            persona_id,
                            skill_id,
                            position
                        )
                        VALUES (?, ?, ?)
                        """,
                        [
                            (persona_id, skill_id, position)
                            for position, skill_id in enumerate(skill_ids)
                        ],
                    )

                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    @asynccontextmanager
    async def _connect(
        self,
    ) -> AsyncIterator[aiosqlite.Connection]:
        """Open a connection with referential integrity enabled."""

        connection = await aiosqlite.connect(self._database_path)

        try:
            connection.row_factory = aiosqlite.Row
            await connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        finally:
            await connection.close()
