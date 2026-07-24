"""Install curated loops once as ordinary resources in every workspace."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import aiosqlite

from src.app.catalogs.loops import LOOP_CATALOG, LoopCatalogEntry
from src.app.models.loop import (
    LoopAgent,
    LoopChangelogEntry,
    LoopDocument,
    LoopOutputContract,
    LoopStopConditions,
)
from src.app.repositories.loops.loop_repository_mapping import (
    insert_agents,
    insert_changelog,
    insert_loop,
)
from src.app.services.loop_validation import document_content


CATALOG_ACTOR_ID = "system:catalog"


async def seed_loop_catalog(
    *,
    database_path: str | Path,
    catalog: Sequence[LoopCatalogEntry] = LOOP_CATALOG,
    id_factory: Callable[[], str] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> int:
    """Install each missing catalog loop once per existing workspace."""

    create_id = id_factory or _create_identifier
    now = clock or _utc_now
    connection = await aiosqlite.connect(database_path)
    connection.row_factory = aiosqlite.Row
    try:
        await connection.execute("PRAGMA foreign_keys = ON")
        await connection.execute("BEGIN IMMEDIATE")
        workspace_ids = await _workspace_ids(connection)
        inserted = 0
        for workspace_id in workspace_ids:
            for definition in catalog:
                if await _is_installed(
                    connection, workspace_id, definition.id
                ):
                    continue
                document = _build_document(
                    definition=definition,
                    workspace_id=workspace_id,
                    create_id=create_id,
                    created_at=now(),
                )
                await insert_loop(connection, document)
                await insert_agents(connection, document)
                await insert_changelog(
                    connection,
                    LoopChangelogEntry(
                        id=create_id(),
                        loop_id=document.id,
                        workspace_id=workspace_id,
                        change_type="created",
                        actor_id=CATALOG_ACTOR_ID,
                        changed_at=document.created_at,
                        diff=None,
                        content=document_content(document),
                    ),
                )
                await connection.execute(
                    """
                    INSERT INTO loop_catalog_installations (
                        workspace_id, catalog_loop_id, loop_id, installed_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        workspace_id,
                        definition.id,
                        document.id,
                        document.created_at.isoformat(),
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


async def _workspace_ids(
    connection: aiosqlite.Connection,
) -> tuple[str, ...]:
    """Return existing workspace identifiers in deterministic order."""

    cursor = await connection.execute(
        "SELECT id FROM workspaces ORDER BY id"
    )
    try:
        rows = await cursor.fetchall()
    finally:
        await cursor.close()
    return tuple(str(row["id"]) for row in rows)


async def _is_installed(
    connection: aiosqlite.Connection,
    workspace_id: str,
    catalog_loop_id: str,
) -> bool:
    """Return whether a catalog definition was previously installed."""

    cursor = await connection.execute(
        """
        SELECT 1
        FROM loop_catalog_installations
        WHERE workspace_id = ? AND catalog_loop_id = ?
        """,
        (workspace_id, catalog_loop_id),
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
) -> LoopDocument:
    """Materialize a catalog entry as a normal mutable loop."""

    return LoopDocument(
        id=create_id(),
        workspace_id=workspace_id,
        title=definition.title,
        description=definition.description,
        flow=definition.flow,
        status="active",
        stop_conditions=LoopStopConditions(
            max_iterations=definition.max_iterations
        ),
        agents=tuple(
            LoopAgent(
                id=create_id(),
                model_id=agent.model_id,
                persona_id=agent.persona_id,
                role=agent.role,
            )
            for agent in definition.agents
        ),
        output_contract=LoopOutputContract(
            type=definition.output_type,
            description=definition.output_description,
            files=definition.output_files,
            schema=definition.output_schema,
        ),
        created_at=created_at,
        created_by=CATALOG_ACTOR_ID,
        updated_at=created_at,
        updated_by=CATALOG_ACTOR_ID,
    )


def _create_identifier() -> str:
    """Create one opaque persisted identifier."""

    return uuid4().hex


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(UTC)
