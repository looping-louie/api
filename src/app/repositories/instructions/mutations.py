"""Create, update, and delete operations for instruction persistence."""

from __future__ import annotations

from typing import Any

import aiosqlite

from src.app.services.persona_skills import (
    DefinitionDocument,
    DefinitionType,
)

from .mapping import (
    normalize_name,
    serialize_datetime,
    serialize_metadata,
)


class InstructionMutationMixin:
    """Provide custom-instruction mutations to the SQLite repository."""

    async def create(
        self,
        document: DefinitionDocument,
    ) -> DefinitionDocument:
        """Insert one instruction document."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                await connection.execute(
                    f"""
                    INSERT INTO instructions (
                        id,
                        instruction_type,
                        origin,
                        {self._owner_column},
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
                        normalize_name(document.name),
                        document.description,
                        document.instructions,
                        serialize_metadata(document.metadata),
                        document.version,
                        serialize_datetime(document.created_at),
                        serialize_datetime(document.updated_at),
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        return document

    async def update(
        self,
        document: DefinitionDocument,
        *,
        expected_version: int,
    ) -> DefinitionDocument | None:
        """
        Update one document when its stored version matches.

        None means that the document was deleted or modified concurrently.
        """

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                cursor = await connection.execute(
                    f"""
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
                                            AND {self._owner_column} = ?
                      AND instruction_type = ?
                      AND version = ?
                    """,
                    (
                        document.name,
                        normalize_name(document.name),
                        document.description,
                        document.instructions,
                        serialize_metadata(document.metadata),
                        document.version,
                        serialize_datetime(document.updated_at),
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
        instruction_type: DefinitionType,
        instruction_id: str,
    ) -> bool:
        """Delete one instruction and report whether it existed."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                cursor = await connection.execute(
                    f"""
                    DELETE FROM instructions
                    WHERE id = ?
                      AND origin = 'custom'
                      AND {self._owner_column} = ?
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

    def _connect(self) -> Any:
        """Return the concrete repository connection context manager."""

        raise NotImplementedError

    async def _get_owned_custom_with_connection(
        self,
        *,
        connection: aiosqlite.Connection,
        workspace_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
    ) -> DefinitionDocument | None:
        """Return one owned custom instruction using an open connection."""

        raise NotImplementedError
