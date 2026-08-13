"""Workspace availability operations for instruction persistence."""

from __future__ import annotations

from typing import Any

from src.app.services.instructions import (
    AvailableInstructionDocument,
    AvailableInstructionSummary,
    InstructionType,
)

from .mapping import (
    escape_like,
    normalize_search,
    to_available_document,
    to_available_summary,
)


class InstructionAvailabilityMixin:
    """Provide workspace-library queries to the SQLite repository."""

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
                i.updated_at,
                json_extract(i.metadata_json, '$.category') AS category
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

        normalized_search = normalize_search(search)

        if normalized_search is not None:
            pattern = f"%{escape_like(normalized_search)}%"
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
            to_available_summary(
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

        return to_available_document(
            row,
            workspace_id=workspace_id,
        )

    def _connect(self) -> Any:
        """Return the concrete repository connection context manager."""

        raise NotImplementedError
