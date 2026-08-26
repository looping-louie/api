"""SQLite persistence for workspace execution defaults."""

from __future__ import annotations

import json
from datetime import datetime

from src.app.models.workspace import WorkspaceDefaults, WorkspaceDocument
from src.app.models.pipeline import PipelineHarness
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase


class SqliteWorkspaceRepository:
    """Store workspace-owned configuration in SQLite."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Initialize the repository with the shared SQLite database."""

        self._database = database

    async def create(
        self,
        *,
        workspace: WorkspaceDocument,
        owner_id: str,
    ) -> WorkspaceDocument:
        """Create a workspace and an owner membership in one transaction."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO workspaces (id, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        workspace.id,
                        workspace.name,
                        workspace.created_at.isoformat(),
                        workspace.updated_at.isoformat(),
                    ),
                )
                await connection.execute(
                    '''
                    INSERT INTO workspace_memberships (
                        workspace_id, user_id, role, is_default, created_at
                    ) VALUES (
                        ?, ?, 'owner',
                        CASE WHEN EXISTS (
                            SELECT 1
                            FROM workspace_memberships
                            WHERE user_id = ? AND is_default = 1
                        ) THEN 0 ELSE 1 END,
                        ?
                    )
                    ''',
                    (
                        workspace.id,
                        owner_id,
                        owner_id,
                        workspace.created_at.isoformat(),
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return workspace

    async def list_for_user(self, *, user_id: str) -> list[WorkspaceDocument]:
        """Return every workspace available to one user."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT w.id, w.name, w.created_at, w.updated_at
                FROM workspaces AS w
                INNER JOIN workspace_memberships AS membership
                    ON membership.workspace_id = w.id
                WHERE membership.user_id = ?
                ORDER BY membership.is_default DESC, w.created_at ASC, w.id ASC
                ''',
                (user_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return [self._workspace_from_row(row) for row in rows]

    async def get_workspace(self, *, workspace_id: str) -> WorkspaceDocument:
        """Return one Workspace known to have an active membership."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, name, created_at, updated_at
                FROM workspaces
                WHERE id = ?
                ''',
                (workspace_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        if row is None:
            raise RuntimeError('Workspace membership references no Workspace.')
        return self._workspace_from_row(row)

    async def update_workspace(
        self,
        *,
        workspace: WorkspaceDocument,
    ) -> WorkspaceDocument:
        """Persist mutable Workspace metadata."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                cursor = await connection.execute(
                    '''
                    UPDATE workspaces
                    SET name = ?, updated_at = ?
                    WHERE id = ?
                    RETURNING id, name, created_at, updated_at
                    ''',
                    (
                        workspace.name,
                        workspace.updated_at.isoformat(),
                        workspace.id,
                    ),
                )
                try:
                    row = await cursor.fetchone()
                finally:
                    await cursor.close()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        if row is None:
            raise RuntimeError('Workspace update did not return a Workspace.')
        return self._workspace_from_row(row)

    async def get_defaults(
        self,
        *,
        workspace_id: str,
    ) -> WorkspaceDefaults | None:
        """Return the workspace defaults when configured."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT workspace_id, model_id, harness_json, updated_at
                FROM workspace_execution_defaults
                WHERE workspace_id = ?
                ''',
                (workspace_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        if row is None:
            return None
        return self._defaults_from_row(row)

    async def replace_defaults(
        self,
        *,
        defaults: WorkspaceDefaults,
    ) -> WorkspaceDefaults:
        """Persist the complete workspace default configuration."""

        async with self._database.connect() as connection:
            await connection.execute(
                '''
                INSERT INTO workspace_execution_defaults (
                    workspace_id, model_id, harness_json, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT (workspace_id) DO UPDATE SET
                    model_id = excluded.model_id,
                    harness_json = excluded.harness_json,
                    updated_at = excluded.updated_at
                ''',
                (
                    defaults.workspace_id,
                    defaults.model_id,
                    self._harness_json(defaults.harness),
                    defaults.updated_at.isoformat(),
                ),
            )
            await connection.commit()
        return defaults

    @staticmethod
    def _defaults_from_row(row: object) -> WorkspaceDefaults:
        """Deserialize one SQLite row to its typed domain model."""

        values = dict(row)  # type: ignore[arg-type]
        model_id = values['model_id']
        harness_value = values['harness_json']
        harness_data = (
            json.loads(str(harness_value))
            if harness_value is not None
            else None
        )
        return WorkspaceDefaults(
            workspace_id=str(values['workspace_id']),
            model_id=str(model_id) if model_id is not None else None,
            harness=(
                PipelineHarness(
                    kind=str(harness_data['kind']),
                    version=str(harness_data['version']),
                    config=dict(harness_data['config']),
                )
                if harness_data is not None
                else None
            ),
            updated_at=datetime.fromisoformat(
                str(values['updated_at']),
            ),
        )

    @staticmethod
    def _workspace_from_row(row: object) -> WorkspaceDocument:
        """Deserialize one SQLite row to a workspace document."""

        values = dict(row)  # type: ignore[arg-type]
        return WorkspaceDocument(
            id=str(values['id']),
            name=str(values['name']),
            created_at=datetime.fromisoformat(str(values['created_at'])),
            updated_at=datetime.fromisoformat(str(values['updated_at'])),
        )

    @staticmethod
    def _harness_json(harness: PipelineHarness | None) -> str | None:
        """Serialize a Harness override without creating an inherited value."""

        if harness is None:
            return None
        return json.dumps(
            {
                'kind': harness.kind,
                'version': harness.version,
                'config': dict(harness.config),
            },
            sort_keys=True,
        )
