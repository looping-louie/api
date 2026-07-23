"""SQLite persistence for personas and skills."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import aiosqlite

from src.app.services.shared.instruction_service import (
    InstructionDocument,
    InstructionSummary,
    InstructionType,
)


class SqliteInstructionRepository:
    """Persists persona and skill instruction documents in SQLite."""

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self._database_path = Path(database_path)

    async def list_summaries(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
    ) -> list[InstructionSummary]:
        """Return summaries for one instruction type and workspace."""

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
            self._to_summary(row)
            for row in rows
        ]

    async def get(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument | None:
        """Return one complete instruction document."""

        async with self._connect() as connection:
            return await self._get_with_connection(
                connection=connection,
                workspace_id=workspace_id,
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

    async def create(
        self,
        document: InstructionDocument,
    ) -> InstructionDocument:
        """Insert one instruction document."""

        async with self._connect() as connection:
            try:
                await connection.execute(
                    "BEGIN IMMEDIATE"
                )
                await connection.execute(
                    """
                    INSERT INTO instructions (
                        id,
                        instruction_type,
                        origin,
                        owner_workspace_id,
                        source_instruction_id,
                        name,
                        name_key,
                        description,
                        content,
                        metadata_json,
                        catalog_version,
                        checksum,
                        enabled_by_default,
                        deprecated,
                        version,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        ?, ?, 'custom', ?, NULL, ?, ?, ?, ?, ?,
                        NULL, NULL, 1, 0, ?, ?, ?
                    )
                    """,
                    (
                        document.id,
                        document.instruction_type,
                        document.workspace_id,
                        document.name,
                        self._normalize_name(document.name),
                        document.description,
                        document.instructions,
                        self._serialize_metadata(document.metadata),
                        document.version,
                        self._serialize_datetime(document.created_at),
                        self._serialize_datetime(document.updated_at),
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        return document

    async def update(
        self,
        document: InstructionDocument,
        *,
        expected_version: int,
    ) -> InstructionDocument | None:
        """
        Update one document when its stored version matches.

        None means that the document was deleted or modified concurrently.
        """

        async with self._connect() as connection:
            try:
                await connection.execute(
                    "BEGIN IMMEDIATE"
                )
                cursor = await connection.execute(
                    """
                    UPDATE instructions
                    SET
                        name = ?,
                        name_key = ?,
                        description = ?,
                        content = ?,
                        metadata_json = ?,
                        version = ?,
                        updated_at = ?
                    WHERE id = ?
                      AND origin = 'custom'
                      AND owner_workspace_id = ?
                      AND instruction_type = ?
                      AND version = ?
                    """,
                    (
                        document.name,
                        self._normalize_name(document.name),
                        document.description,
                        document.instructions,
                        self._serialize_metadata(document.metadata),
                        document.version,
                        self._serialize_datetime(document.updated_at),
                        document.id,
                        document.workspace_id,
                        document.instruction_type,
                        expected_version,
                    ),
                )

                try:
                    updated = cursor.rowcount == 1
                finally:
                    await cursor.close()

                if not updated:
                    await connection.rollback()
                    return None

                stored = await self._get_with_connection(
                    connection=connection,
                    workspace_id=document.workspace_id,
                    instruction_type=document.instruction_type,
                    instruction_id=document.id,
                )
                await connection.commit()

                return stored
            except Exception:
                await connection.rollback()
                raise

    async def delete(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> bool:
        """Delete one instruction and report whether it existed."""

        async with self._connect() as connection:
            try:
                await connection.execute(
                    "BEGIN IMMEDIATE"
                )
                cursor = await connection.execute(
                    """
                    DELETE FROM instructions
                    WHERE id = ?
                      AND origin = 'custom'
                      AND owner_workspace_id = ?
                      AND instruction_type = ?
                    """,
                    (
                        instruction_id,
                        workspace_id,
                        instruction_type,
                    ),
                )

                try:
                    deleted = cursor.rowcount == 1
                finally:
                    await cursor.close()

                await connection.commit()
                return deleted
            except Exception:
                await connection.rollback()
                raise

    async def _get_with_connection(
        self,
        *,
        connection: aiosqlite.Connection,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument | None:
        cursor = await connection.execute(
            """
            SELECT
                id,
                owner_workspace_id AS workspace_id,
                instruction_type,
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

        return self._to_document(row)

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
    def _to_summary(
        row: aiosqlite.Row,
    ) -> InstructionSummary:
        return InstructionSummary(
            id=str(row["id"]),
            name=str(row["name"]),
            description=str(row["description"]),
            version=int(row["version"]),
            created_at=SqliteInstructionRepository._parse_datetime(
                row["created_at"],
            ),
            updated_at=SqliteInstructionRepository._parse_datetime(
                row["updated_at"],
            ),
        )

    @staticmethod
    def _to_document(
        row: aiosqlite.Row,
    ) -> InstructionDocument:
        return InstructionDocument(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            instruction_type=cast(
                InstructionType,
                str(row["instruction_type"]),
            ),
            name=str(row["name"]),
            description=str(row["description"]),
            instructions=str(row["content"]),
            metadata=SqliteInstructionRepository._parse_metadata(
                row["metadata_json"],
            ),
            version=int(row["version"]),
            created_at=SqliteInstructionRepository._parse_datetime(
                row["created_at"],
            ),
            updated_at=SqliteInstructionRepository._parse_datetime(
                row["updated_at"],
            ),
        )

    @staticmethod
    def _normalize_name(name: str) -> str:
        return " ".join(
            name.strip().casefold().split()
        )

    @staticmethod
    def _serialize_metadata(
        metadata: Mapping[str, Any],
    ) -> str:
        return json.dumps(
            dict(metadata),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _parse_metadata(
        raw_metadata: object,
    ) -> dict[str, Any]:
        parsed = json.loads(
            str(raw_metadata),
        )

        if not isinstance(parsed, dict):
            raise ValueError(
                "Stored instruction metadata must be a JSON object."
            )

        return parsed

    @staticmethod
    def _serialize_datetime(value: datetime) -> str:
        return value.isoformat()

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        serialized = str(value)

        if serialized.endswith("Z"):
            serialized = f"{serialized[:-1]}+00:00"

        return datetime.fromisoformat(serialized)
