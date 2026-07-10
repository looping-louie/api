"""SQLite persistence for encrypted provider credentials."""

from datetime import datetime
from typing import Protocol

import aiosqlite

from src.app.models.providers import ProviderCredential
from src.app.repositories.sqlite_database import SqliteDatabase


class ProviderRepository(Protocol):
    """Persistence operations required by ProviderService."""

    async def list_for_org(
        self,
        org_id: str,
    ) -> list[ProviderCredential]:
        """Return all provider configurations for one organisation."""

    async def get(
        self,
        org_id: str,
        provider: str,
    ) -> ProviderCredential | None:
        """Return one provider configuration."""

    async def upsert(
        self,
        credential: ProviderCredential,
    ) -> ProviderCredential:
        """Create or replace one provider configuration."""

    async def set_enabled(
        self,
        org_id: str,
        provider: str,
        enabled: bool,
        enabled_by: str,
        enabled_on: datetime | None,
        updated_at: datetime,
    ) -> ProviderCredential:
        """Enable or disable one provider."""

    async def unset(
        self,
        org_id: str,
        provider: str,
        updated_at: datetime,
    ) -> None:
        """Delete one stored provider configuration."""


class SqliteProviderRepository:
    """SQLite implementation of ProviderRepository."""

    _SCHEMA = (
        """
        CREATE TABLE IF NOT EXISTS provider_credentials (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            enabled_by TEXT,
            enabled_on TEXT,
            key_trimmed TEXT,
            key_ciphertext TEXT,
            key_version INTEGER NOT NULL DEFAULT 1,
            base_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(org_id, provider)
        )
        """,
    )

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared database dependency."""

        self._database = database

    async def list_for_org(
        self,
        org_id: str,
    ) -> list[ProviderCredential]:
        """Return all provider configurations for one organisation."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                SELECT *
                FROM provider_credentials
                WHERE org_id = ?
                ORDER BY provider
                """,
                (org_id,),
            )
            rows = await cursor.fetchall()

        return [self._row_to_credential(row) for row in rows]

    async def get(
        self,
        org_id: str,
        provider: str,
    ) -> ProviderCredential | None:
        """Return one provider configuration."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                SELECT *
                FROM provider_credentials
                WHERE org_id = ? AND provider = ?
                """,
                (org_id, provider),
            )
            row = await cursor.fetchone()

        return self._row_to_credential(row) if row is not None else None

    async def upsert(
        self,
        credential: ProviderCredential,
    ) -> ProviderCredential:
        """Create or replace one provider configuration."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            await connection.execute(
                """
                INSERT INTO provider_credentials (
                    id,
                    org_id,
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
                ON CONFLICT(org_id, provider) DO UPDATE SET
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

        stored = await self.get(
            credential.org_id,
            credential.provider,
        )

        if stored is None:
            raise RuntimeError("Provider credential was not persisted.")

        return stored

    async def set_enabled(
        self,
        org_id: str,
        provider: str,
        enabled: bool,
        enabled_by: str,
        enabled_on: datetime | None,
        updated_at: datetime,
    ) -> ProviderCredential:
        """Enable or disable one provider."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                UPDATE provider_credentials
                SET enabled = ?,
                    enabled_by = ?,
                    enabled_on = ?,
                    updated_at = ?
                WHERE org_id = ? AND provider = ?
                """,
                (
                    int(enabled),
                    enabled_by,
                    self._format_datetime(enabled_on),
                    updated_at.isoformat(),
                    org_id,
                    provider,
                ),
            )
            await connection.commit()

        if cursor.rowcount == 0:
            raise KeyError(
                f"Provider '{provider}' is not configured."
            )

        stored = await self.get(org_id, provider)

        if stored is None:
            raise RuntimeError("Provider state could not be reloaded.")

        return stored

    async def unset(
        self,
        org_id: str,
        provider: str,
        updated_at: datetime,
    ) -> None:
        """Delete one stored provider configuration."""

        del updated_at
        await self._ensure_schema()

        async with self._database.connect() as connection:
            await connection.execute(
                """
                DELETE FROM provider_credentials
                WHERE org_id = ? AND provider = ?
                """,
                (org_id, provider),
            )
            await connection.commit()

    async def _ensure_schema(self) -> None:
        """Create the provider schema when first used."""

        await self._database.ensure_schema(
            schema_name="provider_credentials",
            statements=self._SCHEMA,
        )

    @staticmethod
    def _credential_values(
        credential: ProviderCredential,
    ) -> tuple:
        """Convert a credential into SQLite values."""

        return (
            credential.id,
            credential.org_id,
            credential.provider,
            int(credential.enabled),
            credential.enabled_by,
            SqliteProviderRepository._format_datetime(
                credential.enabled_on
            ),
            credential.key_trimmed,
            credential.key_ciphertext,
            credential.key_version,
            credential.base_url,
            credential.created_at.isoformat(),
            credential.updated_at.isoformat(),
        )

    @staticmethod
    def _row_to_credential(
        row: aiosqlite.Row,
    ) -> ProviderCredential:
        """Convert a SQLite row into a provider credential."""

        return ProviderCredential(
            id=row["id"],
            org_id=row["org_id"],
            provider=row["provider"],
            enabled=bool(row["enabled"]),
            enabled_by=row["enabled_by"],
            enabled_on=SqliteProviderRepository._parse_datetime(
                row["enabled_on"]
            ),
            key_trimmed=row["key_trimmed"],
            key_ciphertext=row["key_ciphertext"],
            key_version=int(row["key_version"]),
            base_url=row["base_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _format_datetime(value: datetime | None) -> str | None:
        """Serialise an optional datetime."""

        return value.isoformat() if value is not None else None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse an optional datetime."""

        return datetime.fromisoformat(value) if value else None
