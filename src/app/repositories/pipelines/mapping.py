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
from src.app.models.execution import ModelTarget
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
            id, workspace_id, name, description, status, model_target_json,
            harness_json,
            created_at, created_by, updated_at, updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document.id,
            document.workspace_id,
            document.name,
            document.description,
            document.status,
            serialize_json(_model_target_value(document.model_target)),
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
    dependencies = [
        (
            document.workspace_id,
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
                workspace_id, pipeline_id, dependent_position,
                dependency_activity_id, condition
            ) VALUES (?, ?, ?, ?, ?)
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
        SELECT position, activity_id
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
    dependency_cursor = await connection.execute(
        """
        SELECT dependent_position, dependency_activity_id, condition
        FROM pipeline_step_dependencies
        WHERE workspace_id = ? AND pipeline_id = ?
        ORDER BY dependent_position ASC, rowid ASC
        """,
        (row['workspace_id'], row['id']),
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
        workspace_id=str(row["workspace_id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        status=cast(PipelineStatus, row["status"]),
        model_target=_to_model_target(row['model_target_json']),
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


def _to_model_target(value: str | None) -> ModelTarget | None:
    """Build an explicit model target when an override is persisted."""

    if value is None:
        return None
    parsed = deserialize_json_object(value)
    if (
        parsed is None
        or not isinstance(parsed.get('linked_service_id'), str)
        or not isinstance(parsed.get('model_id'), str)
    ):
        raise RuntimeError('Pipeline model target is invalid.')
    return ModelTarget(
        linked_service_id=parsed['linked_service_id'],
        model_id=parsed['model_id'],
    )


def _model_target_value(model_target: ModelTarget | None) -> dict[str, str] | None:
    """Serialize an optional model target for a nullable JSON column."""

    if model_target is None:
        return None
    return {
        'linked_service_id': model_target.linked_service_id,
        'model_id': model_target.model_id,
    }


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
