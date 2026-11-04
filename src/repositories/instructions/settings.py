"""Project enablement settings for instruction persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class InstructionSettingsMixin:
    """Provide workspace enablement operations to the SQLite repository."""

    async def set_enabled(
        self,
        *,
        project_id: str,
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
                    f"""
                    SELECT 1
                    FROM instructions AS i
                    LEFT JOIN {self._settings_table} AS settings
                        ON settings.instruction_id = i.id
                       AND settings.{self._settings_owner_column} = ?
                    WHERE i.id = ?
                      AND i.deprecated = 0
                      AND (
                            i.origin = 'builtin'
                            OR (
                                i.origin = 'custom'
                                AND i.{self._owner_column} = ?
                            )
                            OR (
                                i.origin = 'marketplace'
                                AND settings.instruction_id IS NOT NULL
                            )
                      )
                    LIMIT 1
                    """,
                    (
                        project_id,
                        instruction_id,
                        project_id,
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
                    f"""
                    INSERT INTO {self._settings_table} (
                        {self._settings_owner_column},
                        instruction_id,
                        enabled,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT({self._settings_owner_column}, instruction_id)
                    DO UPDATE SET
                        enabled = excluded.enabled,
                        updated_at = excluded.updated_at
                    """,
                    (
                        project_id,
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
        project_id: str,
        instruction_id: str,
    ) -> bool:
        """Return whether an active visible instruction is selectable."""

        async with self._connect() as connection:
            cursor = await connection.execute(
                f"""
                SELECT
                    COALESCE(
                        settings.enabled,
                        i.enabled_by_default
                    ) AS enabled
                FROM instructions AS i
                     LEFT JOIN {self._settings_table} AS settings
                    ON settings.instruction_id = i.id
                         AND settings.{self._settings_owner_column} = ?
                WHERE i.id = ?
                  AND i.deprecated = 0
                  AND (
                        i.origin = 'builtin'
                        OR (
                            i.origin = 'custom'
                            AND i.{self._owner_column} = ?
                        )
                        OR (
                            i.origin = 'marketplace'
                            AND settings.instruction_id IS NOT NULL
                        )
                  )
                LIMIT 1
                """,
                (
                    project_id,
                    instruction_id,
                    project_id,
                ),
            )

            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()

        return row is not None and bool(row["enabled"])

    def _connect(self) -> Any:
        """Return the concrete repository connection context manager."""

        raise NotImplementedError
