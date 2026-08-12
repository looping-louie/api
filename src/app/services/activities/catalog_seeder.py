"""Install curated loop activities once in every workspace."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import aiosqlite

from src.app.catalogs.loops import LOOP_CATALOG, LoopCatalogEntry
from src.app.models.activity import ActivityChangelogEntry, ActivityDocument


CATALOG_ACTOR_ID = 'system:catalog'


async def seed_activity_catalog(
    *,
    database_path: str | Path,
    catalog: Sequence[LoopCatalogEntry] = LOOP_CATALOG,
    id_factory: Callable[[], str] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> int:
    """Install each missing catalog activity once per existing workspace."""

    create_id = id_factory or _create_identifier
    now = clock or _utc_now
    connection = await aiosqlite.connect(database_path)
    connection.row_factory = aiosqlite.Row
    try:
        await connection.execute('PRAGMA foreign_keys = ON')
        await connection.execute('BEGIN IMMEDIATE')
        inserted = 0
        for workspace_id in await _workspace_ids(connection):
            for definition in catalog:
                if await _is_installed(connection, workspace_id, definition.id):
                    continue
                created_at = now()
                document = _build_document(
                    definition=definition,
                    workspace_id=workspace_id,
                    create_id=create_id,
                    created_at=created_at,
                )
                await _insert_document(connection, document)
                await _insert_entry(
                    connection,
                    ActivityChangelogEntry(
                        id=create_id(),
                        activity_id=document.id,
                        workspace_id=workspace_id,
                        change_type='created',
                        actor_id=CATALOG_ACTOR_ID,
                        changed_at=created_at,
                        diff=None,
                        content=_document_content(document),
                    ),
                )
                await connection.execute(
                    'INSERT INTO activity_catalog_installations '
                    '(workspace_id, catalog_activity_id, activity_id, installed_at) '
                    'VALUES (?, ?, ?, ?)',
                    (
                        workspace_id,
                        definition.id,
                        document.id,
                        created_at.isoformat(),
                    ),
                )
                inserted += 1
        await connection.commit()
        return inserted
    except Exception:
        await connection.rollback()
        raise
    finally:
        await connection.close()


async def _workspace_ids(connection: aiosqlite.Connection) -> tuple[str, ...]:
    """Return existing workspace identifiers in deterministic order."""

    cursor = await connection.execute('SELECT id FROM workspaces ORDER BY id')
    try:
        rows = await cursor.fetchall()
    finally:
        await cursor.close()
    return tuple(str(row['id']) for row in rows)


async def _is_installed(
    connection: aiosqlite.Connection,
    workspace_id: str,
    catalog_activity_id: str,
) -> bool:
    """Return whether a catalog activity was previously installed."""

    cursor = await connection.execute(
        'SELECT 1 FROM activity_catalog_installations '
        'WHERE workspace_id = ? AND catalog_activity_id = ?',
        (workspace_id, catalog_activity_id),
    )
    try:
        return await cursor.fetchone() is not None
    finally:
        await cursor.close()


def _build_document(
    *,
    definition: LoopCatalogEntry,
    workspace_id: str,
    create_id: Callable[[], str],
    created_at: datetime,
) -> ActivityDocument:
    """Materialize a catalog loop definition as an active loop activity."""

    return ActivityDocument(
        id=create_id(),
        workspace_id=workspace_id,
        title=definition.title,
        description=definition.description,
        status='active',
        type='loop',
        config={
            'type': 'loop',
            'flow': definition.flow,
            'stop_conditions': {'max_iterations': definition.max_iterations},
            'agents': [
                {
                    'id': create_id(),
                    'model_id': agent.model_id,
                    'persona_id': agent.persona_id,
                    'role': agent.role,
                }
                for agent in definition.agents
            ],
            'output_contract': {
                'type': definition.output_type,
                'description': definition.output_description,
                'files': list(definition.output_files),
                'schema': definition.output_schema,
            },
        },
        created_at=created_at,
        created_by=CATALOG_ACTOR_ID,
        updated_at=created_at,
        updated_by=CATALOG_ACTOR_ID,
    )


async def _insert_document(
    connection: aiosqlite.Connection,
    document: ActivityDocument,
) -> None:
    """Insert one activity using the seeder transaction."""

    await connection.execute(
        'INSERT INTO activities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            document.id,
            document.workspace_id,
            document.title,
            document.description,
            document.status,
            document.type,
            json.dumps(document.config),
            document.created_at.isoformat(),
            document.created_by,
            document.updated_at.isoformat(),
            document.updated_by,
        ),
    )


async def _insert_entry(
    connection: aiosqlite.Connection,
    entry: ActivityChangelogEntry,
) -> None:
    """Insert one activity creation record using the seeder transaction."""

    await connection.execute(
        'INSERT INTO activity_changelog_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            entry.id,
            entry.activity_id,
            entry.workspace_id,
            entry.change_type,
            entry.actor_id,
            entry.changed_at.isoformat(),
            None,
            json.dumps(entry.content),
        ),
    )


def _document_content(document: ActivityDocument) -> dict[str, object]:
    """Return the immutable activity representation retained in history."""

    return {
        'title': document.title,
        'description': document.description,
        'status': document.status,
        'type': document.type,
        'config': document.config,
    }


def _create_identifier() -> str:
    """Create one opaque persisted identifier."""

    return uuid4().hex


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(UTC)