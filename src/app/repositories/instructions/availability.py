"""Workspace availability operations for instruction persistence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.app.catalogs.persona_skills import (
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)
from src.app.services.persona_skills import (
    AvailableDefinitionDocument,
    AvailableDefinitionPage,
    InstructionType,
)

from .mapping import (
    escape_like,
    normalize_search,
    to_available_document,
    to_available_summary,
)


class InstructionAvailabilityMixin:
    """Provide workspace catalog queries to the SQLite repository."""

    async def list_available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
        include_deprecated: bool = False,
        status: CatalogInstructionStatus | None = None,
        categories: Sequence[CatalogInstructionCategory] = (),
        sort: CatalogInstructionSort | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> AvailableDefinitionPage:
        """Return a filtered page of the workspace instruction library."""

        if offset < 0:
            raise ValueError("offset must not be negative.")
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive when supplied.")

        from_where = """
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
            from_where += "\nAND i.deprecated = 0"

        normalized_search = normalize_search(search)

        if normalized_search is not None:
            pattern = f"%{escape_like(normalized_search)}%"
            from_where += """
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

        if status is not None:
            from_where += """
                AND COALESCE(
                    settings.enabled,
                    i.enabled_by_default
                ) = ?
            """
            parameters.append(
                int(status == CatalogInstructionStatus.ENABLED)
            )

        if categories:
            placeholders = ", ".join("?" for _ in categories)
            from_where += (
                "\nAND json_extract(i.metadata_json, '$.category') "
                f"IN ({placeholders})"
            )
            parameters.extend(category.value for category in categories)

        count_query = f"SELECT COUNT(*) AS total {from_where}"
        list_query = f"""
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
            {from_where}
            {self._catalog_order_clause(sort)}
        """
        list_parameters = list(parameters)

        if limit is not None:
            list_query += "\nLIMIT ? OFFSET ?"
            list_parameters.extend((limit, offset))
        elif offset:
            list_query += "\nLIMIT -1 OFFSET ?"
            list_parameters.append(offset)

        async with self._connect() as connection:
            count_cursor = await connection.execute(
                count_query,
                parameters,
            )

            try:
                count_row = await count_cursor.fetchone()
            finally:
                await count_cursor.close()

            cursor = await connection.execute(
                list_query,
                list_parameters,
            )

            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return AvailableDefinitionPage(
            items=tuple(
                to_available_summary(
                    row,
                    workspace_id=workspace_id,
                )
                for row in rows
            ),
            total=(
                int(count_row["total"])
                if count_row is not None
                else 0
            ),
        )

    @staticmethod
    def _catalog_order_clause(
        sort: CatalogInstructionSort | None,
    ) -> str:
        """Return a safe deterministic SQL ordering for a catalog query."""

        if sort == CatalogInstructionSort.ALPHABETICAL_DESC:
            return """
                ORDER BY
                    i.name_key COLLATE NOCASE DESC,
                    i.name COLLATE NOCASE DESC,
                    i.id DESC
            """

        if sort == CatalogInstructionSort.NEWEST:
            return """
                ORDER BY
                    i.created_at DESC,
                    i.name_key COLLATE NOCASE ASC,
                    i.id ASC
            """

        if sort == CatalogInstructionSort.OLDEST:
            return """
                ORDER BY
                    i.created_at ASC,
                    i.name_key COLLATE NOCASE ASC,
                    i.id ASC
            """

        return """
            ORDER BY
                i.name_key COLLATE NOCASE ASC,
                i.name COLLATE NOCASE ASC,
                i.id ASC
        """

    async def get_available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        include_deprecated: bool = False,
    ) -> AvailableDefinitionDocument | None:
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
