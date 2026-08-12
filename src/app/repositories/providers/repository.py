"""SQLite persistence for encrypted provider credentials."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.app.models.provider import ProviderCredential
from src.app.repositories.infrastructure.sqlite_database import (
    SqliteDatabase,
)

from .credential_mapper import (
    credential_values,
    row_to_credential,
)


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
        """Store the shared SQLite connection manager."""

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
            row_to_credential(row)
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

        return row_to_credential(row)

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
                    credential_values(credential),
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
