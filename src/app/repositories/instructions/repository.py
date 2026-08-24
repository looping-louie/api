"""SQLite persistence for personas and skills."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.app.services.persona_skills import (
    DefinitionDocument,
    DefinitionSummary,
    InstructionType,
)

from .availability import InstructionAvailabilityMixin
from .mapping import (
    to_document,
    to_summary,
)
from .mutations import InstructionMutationMixin
from .settings import InstructionSettingsMixin


class SqliteInstructionRepository(
    InstructionAvailabilityMixin,
    InstructionMutationMixin,
    InstructionSettingsMixin,
):
    """Persists persona and skill instruction documents in SQLite."""

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        """Store the SQLite database path."""

        self._database_path = Path(database_path)

    async def list_summaries(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
    ) -> list[DefinitionSummary]:
        """Return owned custom summaries for legacy editing services."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    owner_workspace_id AS workspace_id,
                    instruction_type,
                    name,
                    description,
                    version,
                    created_at,
                    updated_at
                FROM instructions
                WHERE origin = 'custom'
                  AND owner_workspace_id = ?
                  AND instruction_type = ?
                ORDER BY
                    name_key ASC,
                    id ASC
                """,
                (
                    workspace_id,
                    instruction_type,
                ),
            )

            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return [
            to_summary(row)
            for row in rows
        ]

    async def get(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> DefinitionDocument | None:
        """Return one custom instruction owned by the workspace."""

        return await self.get_owned_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

    async def get_owned_custom(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> DefinitionDocument | None:
        """Return a custom instruction owned by the workspace."""

        async with self._connect() as connection:
            return await self._get_owned_custom_with_connection(
                connection=connection,
                workspace_id=workspace_id,
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

    async def _get_owned_custom_with_connection(
        self,
        *,
        connection: aiosqlite.Connection,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> DefinitionDocument | None:
        """Return one owned custom instruction using an open connection."""

        cursor = await connection.execute(
            """
            SELECT
                id,
                owner_workspace_id AS workspace_id,
                instruction_type,
                source_instruction_id,
                name,
                description,
                content,
                metadata_json,
                version,
                created_at,
                updated_at
            FROM instructions
            WHERE id = ?
              AND origin = 'custom'
              AND owner_workspace_id = ?
              AND instruction_type = ?
            LIMIT 1
            """,
            (
                instruction_id,
                workspace_id,
                instruction_type,
            ),
        )

        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()

        if row is None:
            return None

        return to_document(row)

    @asynccontextmanager
    async def _connect(
        self,
    ) -> AsyncIterator[aiosqlite.Connection]:
        """Open one SQLite connection with foreign keys enabled."""

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
