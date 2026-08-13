"""SQLite row mapping and write helpers for pipeline persistence."""

from __future__ import annotations

from datetime import datetime
from typing import cast

import aiosqlite

from src.app.models.pipeline import (
    PipelineChangelogEntry,
    PipelineChangeType,
    PipelineDocument,
    PipelineActivityStep,
    PipelineStatus,
)
from src.app.repositories.shared.json_mapping import (
    deserialize_json_object,
    serialize_json,
)


async def insert_pipeline(
    connection: aiosqlite.Connection,
    document: PipelineDocument,
) -> None:
    """Insert one pipeline scalar row."""

    await connection.execute(
        """
        INSERT INTO pipelines (
            id, workspace_id, name, description, status,
            created_at, created_by, updated_at, updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document.id,
            document.workspace_id,
            document.name,
            document.description,
            document.status,
            document.created_at.isoformat(),
            document.created_by,
            document.updated_at.isoformat(),
            document.updated_by,
        ),
    )


async def insert_steps(
    connection: aiosqlite.Connection,
    document: PipelineDocument,
) -> None:
    """Insert all pipeline steps in execution order."""

    await connection.executemany(
        """
        INSERT INTO pipeline_steps (
            workspace_id, pipeline_id, position, activity_id
        ) VALUES (?, ?, ?, ?)
        """,
        [
            (
                document.workspace_id,
                document.id,
                position,
                step.activity_id,
            )
            for position, step in enumerate(document.steps)
        ],
    )


async def insert_changelog(
    connection: aiosqlite.Connection,
    entry: PipelineChangelogEntry,
) -> None:
    """Append one immutable pipeline changelog entry."""

    await connection.execute(
        """
        INSERT INTO pipeline_changelog_entries (
            id, pipeline_id, workspace_id, change_type, actor_id,
            changed_at, diff_json, content_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.id,
            entry.pipeline_id,
            entry.workspace_id,
            entry.change_type,
            entry.actor_id,
            entry.changed_at.isoformat(),
            serialize_json(entry.diff),
            serialize_json(entry.content),
        ),
    )


async def to_document(
    connection: aiosqlite.Connection,
    row: aiosqlite.Row,
) -> PipelineDocument:
    """Build a pipeline document and its ordered steps."""

    cursor = await connection.execute(
        """
        SELECT activity_id
        FROM pipeline_steps
        WHERE workspace_id = ? AND pipeline_id = ?
        ORDER BY position ASC
        """,
        (row["workspace_id"], row["id"]),
    )
    try:
        step_rows = await cursor.fetchall()
    finally:
        await cursor.close()

    return PipelineDocument(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        status=cast(PipelineStatus, row["status"]),
        steps=tuple(_to_step(step_row) for step_row in step_rows),
        created_at=datetime.fromisoformat(row["created_at"]),
        created_by=str(row["created_by"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        updated_by=str(row["updated_by"]),
    )


def _to_step(row: aiosqlite.Row) -> PipelineActivityStep:
    """Build one activity reference step from persistence."""

    return PipelineActivityStep(activity_id=str(row["activity_id"]))


def to_changelog_entry(row: aiosqlite.Row) -> PipelineChangelogEntry:
    """Build one pipeline changelog entry from a database row."""

    return PipelineChangelogEntry(
        id=str(row["id"]),
        pipeline_id=str(row["pipeline_id"]),
        workspace_id=str(row["workspace_id"]),
        change_type=cast(PipelineChangeType, row["change_type"]),
        actor_id=str(row["actor_id"]),
        changed_at=datetime.fromisoformat(row["changed_at"]),
        diff=deserialize_json_object(row["diff_json"]),
        content=deserialize_json_object(row["content_json"]),
    )


def list_filter(
    *,
    workspace_id: str,
    status: PipelineStatus | None,
    search: str | None,
) -> tuple[str, tuple[object, ...]]:
    """Build the fixed list predicates and bound values."""

    clauses = ["workspace_id = ?"]
    parameters: list[object] = [workspace_id]
    if status is None:
        clauses.append("status <> 'archived'")
    else:
        clauses.append("status = ?")
        parameters.append(status)
    if search is not None:
        clauses.append(
            "(LOWER(name) LIKE ? OR LOWER(description) LIKE ?)"
        )
        pattern = f"%{search.casefold()}%"
        parameters.extend((pattern, pattern))
    return " AND ".join(clauses), tuple(parameters)


async def count_pipelines(
    connection: aiosqlite.Connection,
    where: str,
    parameters: tuple[object, ...],
) -> int:
    """Count pipelines matching an internally-built predicate."""

    cursor = await connection.execute(
        f"SELECT COUNT(*) AS total FROM pipelines WHERE {where}",
        parameters,
    )
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    return int(row["total"]) if row is not None else 0
