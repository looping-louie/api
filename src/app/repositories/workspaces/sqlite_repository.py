"""SQLite persistence for workspace execution defaults."""

from __future__ import annotations

import json
from datetime import datetime

from src.app.models.workspace import ModelTarget, WorkspaceDefaults
from src.app.models.pipeline import PipelineHarness
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase


class SqliteWorkspaceRepository:
    """Store workspace-owned configuration in SQLite."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Initialize the repository with the shared SQLite database."""

        self._database = database

    async def get(
        self,
        *,
        workspace_id: str,
    ) -> WorkspaceDefaults | None:
        """Return the workspace defaults when configured."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT workspace_id, model_target_json, harness_json, updated_at
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

    async def replace(
        self,
        *,
        defaults: WorkspaceDefaults,
    ) -> WorkspaceDefaults:
        """Persist the complete workspace default configuration."""

        async with self._database.connect() as connection:
            await connection.execute(
                '''
                INSERT INTO workspace_execution_defaults (
                    workspace_id, model_target_json, harness_json, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT (workspace_id) DO UPDATE SET
                    model_target_json = excluded.model_target_json,
                    harness_json = excluded.harness_json,
                    updated_at = excluded.updated_at
                ''',
                (
                    defaults.workspace_id,
                    self._model_target_json(defaults.model_target),
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
        model_target_value = values['model_target_json']
        harness_value = values['harness_json']
        model_target_data = (
            json.loads(str(model_target_value))
            if model_target_value is not None
            else None
        )
        harness_data = (
            json.loads(str(harness_value))
            if harness_value is not None
            else None
        )
        return WorkspaceDefaults(
            workspace_id=str(values['workspace_id']),
            model_target=(
                ModelTarget(
                    linked_service_id=str(model_target_data['linked_service_id']),
                    model_id=str(model_target_data['model_id']),
                )
                if model_target_data is not None
                else None
            ),
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
    def _model_target_json(model_target: ModelTarget | None) -> str | None:
        """Serialize a model target without creating an inherited value."""

        if model_target is None:
            return None
        return json.dumps(
            {
                'linked_service_id': model_target.linked_service_id,
                'model_id': model_target.model_id,
            },
            sort_keys=True,
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
