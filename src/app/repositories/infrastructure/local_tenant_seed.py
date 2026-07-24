"""Local workspace seed for development installations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite


async def ensure_local_tenant(
    *,
    database_path: str | Path,
    workspace_id: str = "local-workspace",
    workspace_name: str = "Local workspace",
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
                INSERT INTO workspaces (
                    id,
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    workspace_id,
                    workspace_name,
                    now,
                    now,
                ),
            )

            await connection.execute(
                """
                INSERT INTO workspace_memberships (
                    workspace_id,
                    user_id,
                    role,
                    is_default,
                    created_at
                )
                VALUES (?, ?, 'owner', 1, ?)
                ON CONFLICT(workspace_id, user_id) DO UPDATE SET
                    role = 'owner',
                    is_default = 1
                """,
                (
                    workspace_id,
                    user_id,
                    now,
                ),
            )

            await connection.commit()
        except Exception:
            await connection.rollback()
            raise
