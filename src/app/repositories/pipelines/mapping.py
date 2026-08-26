"""SQLite row mapping and write helpers for pipeline persistence."""

from __future__ import annotations

from datetime import datetime
from typing import cast

import aiosqlite

from src.app.models.pipeline import (
    PipelineChangelogEntry,
    PipelineChangeType,
    PipelineDocument,
    PipelineHarness,
    PipelineHarnessKind,
    PipelineActivityStep,
    PipelineStepDependency,
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
            id, user_id, name, description, status, model_id,
            harness_json,
            created_at, created_by, updated_at, updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document.id,
            document.user_id,
            document.name,
            document.description,
            document.status,
            document.model_id,
            serialize_json(_harness_value(document.harness)),
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
    """Insert all pipeline steps in their declared display order."""

    await connection.executemany(
        """
        INSERT INTO pipeline_steps (
            pipeline_id, position, activity_id
        ) VALUES (?, ?, ?)
        """,
        [
            (
                document.id,
                position,
                step.activity_id,
            )
            for position, step in enumerate(document.steps)
        ],
    )
    dependencies = [
        (
            document.id,
            position,
            dependency.activity_id,
            dependency.condition,
        )
        for position, step in enumerate(document.steps)
        for dependency in step.depends_on
    ]
    if dependencies:
        await connection.executemany(
            """
            INSERT INTO pipeline_step_dependencies (
                pipeline_id, dependent_position,
                dependency_activity_id, condition
            ) VALUES (?, ?, ?, ?)
            """,
            dependencies,
        )


async def insert_changelog(
    connection: aiosqlite.Connection,
    entry: PipelineChangelogEntry,
) -> None:
    """Append one immutable pipeline changelog entry."""

    await connection.execute(
        """
        INSERT INTO pipeline_changelog_entries (
            id, pipeline_id, user_id, change_type, actor_id,
            changed_at, diff_json, content_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.id,
            entry.pipeline_id,
            entry.user_id,
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
        SELECT position, activity_id
        FROM pipeline_steps
        WHERE pipeline_id = ?
        ORDER BY position ASC
        """,
        (row['id'],),
    )
    try:
        step_rows = await cursor.fetchall()
    finally:
        await cursor.close()
    dependency_cursor = await connection.execute(
        """
        SELECT dependent_position, dependency_activity_id, condition
        FROM pipeline_step_dependencies
        WHERE pipeline_id = ?
        ORDER BY dependent_position ASC, rowid ASC
        """,
        (row['id'],),
    )
    try:
        dependency_rows = await dependency_cursor.fetchall()
    finally:
        await dependency_cursor.close()
    dependencies_by_position: dict[int, list[PipelineStepDependency]] = {}
    for dependency_row in dependency_rows:
        dependencies_by_position.setdefault(
            int(dependency_row['dependent_position']),
            [],
        ).append(
            PipelineStepDependency(
                activity_id=str(dependency_row['dependency_activity_id']),
                condition=dependency_row['condition'],
            )
        )

    return PipelineDocument(
        id=str(row["id"]),
        user_id=str(row['user_id']),
        name=str(row["name"]),
        description=str(row["description"]),
        status=cast(PipelineStatus, row["status"]),
        model_id=row['model_id'],
        harness=_to_harness(row['harness_json']),
        steps=tuple(
            _to_step(
                step_row,
                dependencies_by_position.get(int(step_row['position']), []),
            )
            for step_row in step_rows
        ),
        created_at=datetime.fromisoformat(row["created_at"]),
        created_by=str(row["created_by"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        updated_by=str(row["updated_by"]),
    )


def _to_step(
    row: aiosqlite.Row,
    dependencies: list[PipelineStepDependency],
) -> PipelineActivityStep:
    """Build one activity reference step from persistence."""

    return PipelineActivityStep(
        activity_id=str(row["activity_id"]),
        depends_on=tuple(dependencies),
    )


def _to_harness(value: str | None) -> PipelineHarness | None:
    """Build one persisted Pipeline Harness selection."""

    if value is None:
        return None
    parsed = deserialize_json_object(value)
    config = parsed.get('config') if parsed is not None else None
    if (
        parsed is None
        or parsed.get('kind') not in ('louie', 'codex_cli')
        or parsed.get('version') != 'v1'
        or not isinstance(config, dict)
        or config
    ):
        raise RuntimeError('Pipeline harness is invalid.')
    return PipelineHarness(kind=cast(PipelineHarnessKind, parsed['kind']))


def _harness_value(harness: PipelineHarness | None) -> dict[str, object] | None:
    """Serialize an optional Harness for a nullable JSON column."""

    if harness is None:
        return None
    return {
        'kind': harness.kind,
        'version': harness.version,
        'config': dict(harness.config),
    }


def to_changelog_entry(row: aiosqlite.Row) -> PipelineChangelogEntry:
    """Build one pipeline changelog entry from a database row."""

    return PipelineChangelogEntry(
        id=str(row["id"]),
        pipeline_id=str(row["pipeline_id"]),
        user_id=str(row['user_id']),
        change_type=cast(PipelineChangeType, row["change_type"]),
        actor_id=str(row["actor_id"]),
        changed_at=datetime.fromisoformat(row["changed_at"]),
        diff=deserialize_json_object(row["diff_json"]),
        content=deserialize_json_object(row["content_json"]),
    )


def list_filter(
    *,
    user_id: str,
    status: PipelineStatus | None,
    search: str | None,
) -> tuple[str, tuple[object, ...]]:
    """Build the fixed list predicates and bound values."""

    clauses = ['user_id = ?']
    parameters: list[object] = [user_id]
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
