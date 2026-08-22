"""SQLite persistence for persona linked-service selections."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.app.services.personas.types import PersonaLinkedServiceSelection


class SqlitePersonaLinkedServiceSelectionRepository:
    """Persist one linked-service selection for each workspace persona."""

    def __init__(self, database_path: str | Path) -> None:
        """Initialize the repository for one SQLite database."""

        self._database_path = Path(database_path)

    async def get_for_persona(
        self,
        *,
        workspace_id: str,
        persona_id: str,
    ) -> PersonaLinkedServiceSelection | None:
        """Return the stored linked-service selection when one exists."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT linked_service_id, model_id
                FROM persona_linked_service_selections
                WHERE workspace_id = ? AND persona_id = ?
                ''',
                (workspace_id, persona_id),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()

        if row is None:
            return None
        return PersonaLinkedServiceSelection(
            linked_service_id=str(row['linked_service_id']),
            model_id=str(row['model_id']),
        )

    async def replace_for_persona(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        selection: PersonaLinkedServiceSelection,
    ) -> None:
        """Store one workspace-scoped linked-service selection."""

        async with self._connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO persona_linked_service_selections (
                        workspace_id, persona_id, linked_service_id, model_id
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT (workspace_id, persona_id) DO UPDATE SET
                        linked_service_id = excluded.linked_service_id,
                        model_id = excluded.model_id
                    ''',
                    (
                        workspace_id,
                        persona_id,
                        selection.linked_service_id,
                        selection.model_id,
                    ),
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
