"""Mapping helpers for SQLite provider credential rows."""

from datetime import datetime

import aiosqlite

from src.app.models.provider import ProviderCredential


def format_datetime(value: datetime | None) -> str | None:
    """Serialize an optional datetime for SQLite."""

    return value.isoformat() if value is not None else None


def parse_datetime(value: object) -> datetime:
    """Parse a required datetime returned by SQLite."""

    serialized = str(value)
    if serialized.endswith("Z"):
        serialized = f"{serialized[:-1]}+00:00"
    return datetime.fromisoformat(serialized)


def parse_optional_datetime(value: object | None) -> datetime | None:
    """Parse an optional datetime returned by SQLite."""

    return parse_datetime(value) if value is not None else None


def credential_values(
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
    """Convert a credential into SQLite statement values."""

    return (
        credential.id,
        credential.workspace_id,
        credential.provider,
        int(credential.enabled),
        credential.enabled_by,
        format_datetime(credential.enabled_on),
        credential.key_trimmed,
        credential.key_ciphertext,
        credential.key_version,
        credential.base_url,
        credential.created_at.isoformat(),
        credential.updated_at.isoformat(),
    )


def row_to_credential(row: aiosqlite.Row) -> ProviderCredential:
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
        enabled_on=parse_optional_datetime(row["enabled_on"]),
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
        created_at=parse_datetime(row["created_at"]),
        updated_at=parse_datetime(row["updated_at"]),
    )
