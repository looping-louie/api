"""Local Project seed for development installations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite


async def ensure_local_tenant(
    *,
    database_path: str | Path,
    project_id: str = 'local-project',
    project_name: str = 'Local project',
    user_id: str = "local-user",
) -> None:
    """Create the initial local workspace and membership when absent."""

    now = datetime.now(UTC).isoformat()

    async with aiosqlite.connect(database_path) as connection:
        await connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        await connection.execute(
            "BEGIN IMMEDIATE"
        )

        try:
            await connection.execute(
                """
                INSERT INTO users (id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    user_id,
                    now,
                    now,
                ),
            )

            await connection.execute(
                """
                INSERT INTO projects (
                    id,
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    project_id,
                    project_name,
                    now,
                    now,
                ),
            )

            await connection.execute(
                """
                INSERT INTO project_memberships (
                    project_id,
                    user_id,
                    role,
                    is_default,
                    created_at
                )
                VALUES (?, ?, 'owner', 1, ?)
                ON CONFLICT(project_id, user_id) DO UPDATE SET
                    role = 'owner',
                    is_default = 1
                """,
                (
                    project_id,
                    user_id,
                    now,
                ),
            )

            await connection.commit()
        except Exception:
            await connection.rollback()
            raise
