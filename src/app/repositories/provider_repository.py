"""SQLite persistence for encrypted provider credentials."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import aiosqlite

from src.app.models.providers import ProviderCredential
from src.app.repositories.sqlite_database import SqliteDatabase


class ProviderRepository(Protocol):
    """Persistence operations required by ProviderService."""

    async def list_for_workspace(
        self,
        workspace_id: str,
    ) -> list[ProviderCredential]:
        """Return all provider configurations for one workspace."""
        ...

    async def get(
        self,
        workspace_id: str,
        provider: str,
    ) -> ProviderCredential | None:
        """Return one provider configuration."""
        ...

    async def upsert(
        self,
        credential: ProviderCredential,
    ) -> ProviderCredential:
        """Create or replace one provider configuration."""
        ...

    async def set_enabled(
        self,
        workspace_id: str,
        provider: str,
        enabled: bool,
        enabled_by: str | None,
        enabled_on: datetime | None,
        updated_at: datetime,
    ) -> ProviderCredential:
        """Enable or disable one provider."""
        ...

    async def unset(
        self,
        workspace_id: str,
        provider: str,
        updated_at: datetime,
    ) -> None:
        """Delete one stored provider configuration."""
        ...


class SqliteProviderRepository:
    """SQLite implementation of ProviderRepository."""

    def __init__(
        self,
        database: SqliteDatabase,
    ) -> None:
        self._database = database

    async def list_for_workspace(
        self,
        workspace_id: str,
    ) -> list[ProviderCredential]:
        """Return all provider configurations for one workspace."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    workspace_id,
                    provider,
                    enabled,
                    enabled_by,
                    enabled_on,
                    key_trimmed,
                    key_ciphertext,
                    key_version,
                    base_url,
                    created_at,
                    updated_at
                FROM provider_credentials
                WHERE workspace_id = ?
                ORDER BY provider ASC
                """,
                (workspace_id,),
            )

            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return [
            self._row_to_credential(row)
            for row in rows
        ]

    async def get(
        self,
        workspace_id: str,
        provider: str,
    ) -> ProviderCredential | None:
        """Return one provider configuration."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    workspace_id,
                    provider,
                    enabled,
                    enabled_by,
                    enabled_on,
                    key_trimmed,
                    key_ciphertext,
                    key_version,
                    base_url,
                    created_at,
                    updated_at
                FROM provider_credentials
                WHERE workspace_id = ?
                  AND provider = ?
                LIMIT 1
                """,
                (
                    workspace_id,
                    provider,
                ),
            )

            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()

        if row is None:
            return None

        return self._row_to_credential(row)

    async def upsert(
        self,
        credential: ProviderCredential,
    ) -> ProviderCredential:
        """Create or replace one provider configuration."""

        async with self._database.connect() as connection:
            try:
                await connection.execute(
                    "BEGIN IMMEDIATE"
                )
                await connection.execute(
                    """
                    INSERT INTO provider_credentials (
                        id,
                        workspace_id,
                        provider,
                        enabled,
                        enabled_by,
                        enabled_on,
                        key_trimmed,
                        key_ciphertext,
                        key_version,
                        base_url,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(workspace_id, provider) DO UPDATE SET
                        enabled = excluded.enabled,
                        enabled_by = excluded.enabled_by,
                        enabled_on = excluded.enabled_on,
                        key_trimmed = excluded.key_trimmed,
                        key_ciphertext = excluded.key_ciphertext,
                        key_version = excluded.key_version,
                        base_url = excluded.base_url,
                        updated_at = excluded.updated_at
                    """,
                    self._credential_values(credential),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        stored = await self.get(
            credential.workspace_id,
            credential.provider,
        )

        if stored is None:
            raise RuntimeError(
                "Provider credential was not persisted."
            )

        return stored

    async def set_enabled(
        self,
        workspace_id: str,
        provider: str,
        enabled: bool,
        enabled_by: str | None,
        enabled_on: datetime | None,
        updated_at: datetime,
    ) -> ProviderCredential:
        """Enable or disable one provider."""

        async with self._database.connect() as connection:
            try:
                await connection.execute(
                    "BEGIN IMMEDIATE"
                )
                cursor = await connection.execute(
                    """
                    UPDATE provider_credentials
                    SET
                        enabled = ?,
                        enabled_by = ?,
                        enabled_on = ?,
                        updated_at = ?
                    WHERE workspace_id = ?
                      AND provider = ?
                    """,
                    (
                        int(enabled),
                        enabled_by,
                        self._format_datetime(enabled_on),
                        self._format_datetime(updated_at),
                        workspace_id,
                        provider,
                    ),
                )

                try:
                    updated = cursor.rowcount == 1
                finally:
                    await cursor.close()

                if not updated:
                    await connection.rollback()

                    raise KeyError(
                        f"Provider '{provider}' is not configured "
                        f"for workspace '{workspace_id}'."
                    )

                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        stored = await self.get(
            workspace_id,
            provider,
        )

        if stored is None:
            raise RuntimeError(
                "Provider state could not be reloaded."
            )

        return stored

    async def unset(
        self,
        workspace_id: str,
        provider: str,
        updated_at: datetime,
    ) -> None:
        """Delete one stored provider configuration."""

        del updated_at

        async with self._database.connect() as connection:
            try:
                await connection.execute(
                    "BEGIN IMMEDIATE"
                )
                cursor = await connection.execute(
                    """
                    DELETE FROM provider_credentials
                    WHERE workspace_id = ?
                      AND provider = ?
                    """,
                    (
                        workspace_id,
                        provider,
                    ),
                )

                try:
                    await cursor.close()
                finally:
                    await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    @staticmethod
    def _credential_values(
        credential: ProviderCredential,
    ) -> tuple[
        str,
        str,
        str,
        int,
        str | None,
        str | None,
        str | None,
        str | None,
        int,
        str | None,
        str,
        str,
    ]:
        """Convert a credential into SQLite values."""

        return (
            credential.id,
            credential.workspace_id,
            credential.provider,
            int(credential.enabled),
            credential.enabled_by,
            SqliteProviderRepository._format_datetime(
                credential.enabled_on,
            ),
            credential.key_trimmed,
            credential.key_ciphertext,
            credential.key_version,
            credential.base_url,
            SqliteProviderRepository._format_datetime(
                credential.created_at,
            ),
            SqliteProviderRepository._format_datetime(
                credential.updated_at,
            ),
        )

    @staticmethod
    def _row_to_credential(
        row: aiosqlite.Row,
    ) -> ProviderCredential:
        """Convert a SQLite row into a provider credential."""

        return ProviderCredential(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            provider=str(row["provider"]),
            enabled=bool(row["enabled"]),
            enabled_by=(
                str(row["enabled_by"])
                if row["enabled_by"] is not None
                else None
            ),
            enabled_on=SqliteProviderRepository._parse_optional_datetime(
                row["enabled_on"],
            ),
            key_trimmed=(
                str(row["key_trimmed"])
                if row["key_trimmed"] is not None
                else None
            ),
            key_ciphertext=(
                str(row["key_ciphertext"])
                if row["key_ciphertext"] is not None
                else None
            ),
            key_version=int(row["key_version"]),
            base_url=(
                str(row["base_url"])
                if row["base_url"] is not None
                else None
            ),
            created_at=SqliteProviderRepository._parse_datetime(
                row["created_at"],
            ),
            updated_at=SqliteProviderRepository._parse_datetime(
                row["updated_at"],
            ),
        )

    @staticmethod
    def _format_datetime(
        value: datetime | None,
    ) -> str | None:
        """Serialise an optional datetime."""

        if value is None:
            return None

        return value.isoformat()

    @staticmethod
    def _parse_datetime(
        value: object,
    ) -> datetime:
        """Parse a required datetime."""

        serialized = str(value)

        if serialized.endswith("Z"):
            serialized = f"{serialized[:-1]}+00:00"

        return datetime.fromisoformat(serialized)

    @staticmethod
    def _parse_optional_datetime(
        value: object | None,
    ) -> datetime | None:
        """Parse an optional datetime."""

        if value is None:
            return None

        return SqliteProviderRepository._parse_datetime(value)
