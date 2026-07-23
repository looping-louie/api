"""SQLite persistence for personas and skills."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import aiosqlite

from src.app.catalogs.instructions import InstructionOrigin
from src.app.services.shared.instruction_service import (
    AvailableInstructionDocument,
    AvailableInstructionSummary,
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
        """Return one custom instruction owned by the workspace."""

        return await self.get_owned_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

    async def list_available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
        include_deprecated: bool = False,
    ) -> list[AvailableInstructionSummary]:
        """Return the effective instruction library for a workspace."""

        query = """
            SELECT
                i.id,
                i.instruction_type,
                i.origin,
                i.owner_workspace_id,
                i.source_instruction_id,
                i.name,
                i.description,
                COALESCE(
                    settings.enabled,
                    i.enabled_by_default
                ) AS enabled,
                i.enabled_by_default,
                i.deprecated,
                i.catalog_version,
                i.version,
                i.created_at,
                i.updated_at
            FROM instructions AS i
            LEFT JOIN workspace_instruction_settings AS settings
                ON settings.instruction_id = i.id
               AND settings.workspace_id = ?
            WHERE i.instruction_type = ?
              AND (
                    i.origin = 'builtin'
                    OR (
                        i.origin = 'custom'
                        AND i.owner_workspace_id = ?
                    )
                    OR (
                        i.origin = 'marketplace'
                        AND settings.instruction_id IS NOT NULL
                    )
              )
        """
        parameters: list[object] = [
            workspace_id,
            instruction_type,
            workspace_id,
        ]

        if not include_deprecated:
            query += "\nAND i.deprecated = 0"

        normalized_search = self._normalize_search(search)

        if normalized_search is not None:
            pattern = (
                f"%{self._escape_like(normalized_search)}%"
            )
            query += """
                AND (
                    i.name_key LIKE ? ESCAPE '\\'
                    OR lower(i.description) LIKE ? ESCAPE '\\'
                )
            """
            parameters.extend(
                [
                    pattern,
                    pattern,
                ]
            )

        query += """
            ORDER BY
                i.name_key COLLATE NOCASE ASC,
                i.name COLLATE NOCASE ASC,
                i.id ASC
        """

        async with self._connect() as connection:
            cursor = await connection.execute(
                query,
                parameters,
            )

            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return [
            self._to_available_summary(
                row,
                workspace_id=workspace_id,
            )
            for row in rows
        ]

    async def get_available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        include_deprecated: bool = False,
    ) -> AvailableInstructionDocument | None:
        """Resolve one visible instruction, even when it is disabled."""

        deprecated_clause = (
            ""
            if include_deprecated
            else "AND i.deprecated = 0"
        )
        query = f"""
            SELECT
                i.id,
                i.instruction_type,
                i.origin,
                i.owner_workspace_id,
                i.source_instruction_id,
                i.name,
                i.description,
                i.content,
                i.metadata_json,
                COALESCE(
                    settings.enabled,
                    i.enabled_by_default
                ) AS enabled,
                i.enabled_by_default,
                i.deprecated,
                i.catalog_version,
                i.checksum,
                i.version,
                i.created_at,
                i.updated_at
            FROM instructions AS i
            LEFT JOIN workspace_instruction_settings AS settings
                ON settings.instruction_id = i.id
               AND settings.workspace_id = ?
            WHERE i.id = ?
              AND i.instruction_type = ?
              AND (
                    i.origin = 'builtin'
                    OR (
                        i.origin = 'custom'
                        AND i.owner_workspace_id = ?
                    )
                    OR (
                        i.origin = 'marketplace'
                        AND settings.instruction_id IS NOT NULL
                    )
              )
              {deprecated_clause}
            LIMIT 1
        """

        async with self._connect() as connection:
            cursor = await connection.execute(
                query,
                (
                    workspace_id,
                    instruction_id,
                    instruction_type,
                    workspace_id,
                ),
            )

            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()

        if row is None:
            return None

        return self._to_available_document(
            row,
            workspace_id=workspace_id,
        )

    async def get_owned_custom(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument | None:
        """Return a custom instruction owned by the workspace."""

        async with self._connect() as connection:
            return await self._get_owned_custom_with_connection(
                connection=connection,
                workspace_id=workspace_id,
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

    async def set_enabled(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
        enabled: bool,
    ) -> bool:
        """Set an explicit override for a visible active instruction."""

        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean.")

        timestamp = datetime.now(UTC).isoformat()

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                cursor = await connection.execute(
                    """
                    SELECT 1
                    FROM instructions AS i
                    LEFT JOIN workspace_instruction_settings AS settings
                        ON settings.instruction_id = i.id
                       AND settings.workspace_id = ?
                    WHERE i.id = ?
                      AND i.deprecated = 0
                      AND (
                            i.origin = 'builtin'
                            OR (
                                i.origin = 'custom'
                                AND i.owner_workspace_id = ?
                            )
                            OR (
                                i.origin = 'marketplace'
                                AND settings.instruction_id IS NOT NULL
                            )
                      )
                    LIMIT 1
                    """,
                    (
                        workspace_id,
                        instruction_id,
                        workspace_id,
                    ),
                )

                try:
                    visible = await cursor.fetchone()
                finally:
                    await cursor.close()

                if visible is None:
                    await connection.rollback()
                    return False

                await connection.execute(
                    """
                    INSERT INTO workspace_instruction_settings (
                        workspace_id,
                        instruction_id,
                        enabled,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(workspace_id, instruction_id)
                    DO UPDATE SET
                        enabled = excluded.enabled,
                        updated_at = excluded.updated_at
                    """,
                    (
                        workspace_id,
                        instruction_id,
                        int(enabled),
                        timestamp,
                        timestamp,
                    ),
                )
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def is_enabled(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
    ) -> bool:
        """Return whether an active visible instruction is selectable."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    COALESCE(
                        settings.enabled,
                        i.enabled_by_default
                    ) AS enabled
                FROM instructions AS i
                LEFT JOIN workspace_instruction_settings AS settings
                    ON settings.instruction_id = i.id
                   AND settings.workspace_id = ?
                WHERE i.id = ?
                  AND i.deprecated = 0
                  AND (
                        i.origin = 'builtin'
                        OR (
                            i.origin = 'custom'
                            AND i.owner_workspace_id = ?
                        )
                        OR (
                            i.origin = 'marketplace'
                            AND settings.instruction_id IS NOT NULL
                        )
                  )
                LIMIT 1
                """,
                (
                    workspace_id,
                    instruction_id,
                    workspace_id,
                ),
            )

            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()

        return row is not None and bool(row["enabled"])

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
                        ?, ?, 'custom', ?, ?, ?, ?, ?, ?, ?,
                        NULL, NULL, 1, 0, ?, ?, ?
                    )
                    """,
                    (
                        document.id,
                        document.instruction_type,
                        document.workspace_id,
                        document.source_instruction_id,
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

                stored = await self._get_owned_custom_with_connection(
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

    async def _get_owned_custom_with_connection(
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
            source_instruction_id=(
                str(row["source_instruction_id"])
                if row["source_instruction_id"] is not None
                else None
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
    def _to_available_summary(
        row: aiosqlite.Row,
        *,
        workspace_id: str,
    ) -> AvailableInstructionSummary:
        return AvailableInstructionSummary(
            id=str(row["id"]),
            workspace_id=workspace_id,
            instruction_type=cast(
                InstructionType,
                str(row["instruction_type"]),
            ),
            origin=InstructionOrigin(
                str(row["origin"])
            ),
            owner_workspace_id=(
                str(row["owner_workspace_id"])
                if row["owner_workspace_id"] is not None
                else None
            ),
            source_instruction_id=(
                str(row["source_instruction_id"])
                if row["source_instruction_id"] is not None
                else None
            ),
            name=str(row["name"]),
            description=str(row["description"]),
            enabled=bool(row["enabled"]),
            enabled_by_default=bool(
                row["enabled_by_default"]
            ),
            deprecated=bool(row["deprecated"]),
            catalog_version=(
                int(row["catalog_version"])
                if row["catalog_version"] is not None
                else None
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
    def _to_available_document(
        row: aiosqlite.Row,
        *,
        workspace_id: str,
    ) -> AvailableInstructionDocument:
        return AvailableInstructionDocument(
            id=str(row["id"]),
            workspace_id=workspace_id,
            instruction_type=cast(
                InstructionType,
                str(row["instruction_type"]),
            ),
            origin=InstructionOrigin(
                str(row["origin"])
            ),
            owner_workspace_id=(
                str(row["owner_workspace_id"])
                if row["owner_workspace_id"] is not None
                else None
            ),
            source_instruction_id=(
                str(row["source_instruction_id"])
                if row["source_instruction_id"] is not None
                else None
            ),
            name=str(row["name"]),
            description=str(row["description"]),
            instructions=str(row["content"]),
            metadata=SqliteInstructionRepository._parse_metadata(
                row["metadata_json"],
            ),
            enabled=bool(row["enabled"]),
            enabled_by_default=bool(
                row["enabled_by_default"]
            ),
            deprecated=bool(row["deprecated"]),
            catalog_version=(
                int(row["catalog_version"])
                if row["catalog_version"] is not None
                else None
            ),
            checksum=(
                str(row["checksum"])
                if row["checksum"] is not None
                else None
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

    @classmethod
    def _normalize_search(
        cls,
        search: str | None,
    ) -> str | None:
        if search is None:
            return None

        normalized = cls._normalize_name(search)
        return normalized or None

    @staticmethod
    def _escape_like(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
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
