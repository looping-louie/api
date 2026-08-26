"""Migration coverage for logical model override backfill."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / 'migrations'
    / 'sqlite'
    / '0052_logical_model_overrides.sql'
)


def test_logical_model_overrides_migration_backfills_definition_models(
    tmp_path: Path,
) -> None:
    """Legacy definition targets become logical model IDs and agent overrides."""

    database_path = tmp_path / 'logical-model-overrides.db'
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE activities (
            id TEXT PRIMARY KEY,
            model_target_json TEXT,
            config_json TEXT NOT NULL
        );
        CREATE TABLE pipelines (
            id TEXT PRIMARY KEY,
            model_target_json TEXT
        );
        CREATE TABLE workspace_execution_defaults (
            workspace_id TEXT PRIMARY KEY,
            model_target_json TEXT
        );
        """
    )
    target = '{"linked_service_id":"linked-service-1","model_id":"gpt-5"}'
    config = (
        '{"agents":[{"model_target":{"linked_service_id":"linked-service-1",'
        '"model_id":"gpt-5"},"persona_id":"persona-1","role":"generator"}]}'
    )
    connection.execute(
        'INSERT INTO activities (id, model_target_json, config_json) VALUES (?, ?, ?)',
        ('activity-1', target, config),
    )
    connection.execute(
        'INSERT INTO pipelines (id, model_target_json) VALUES (?, ?)',
        ('pipeline-1', target),
    )
    connection.execute(
        'INSERT INTO workspace_execution_defaults (workspace_id, model_target_json) VALUES (?, ?)',
        ('workspace-1', target),
    )

    connection.executescript(MIGRATION_PATH.read_text(encoding='utf-8'))

    activity = connection.execute(
        'SELECT model_id, config_json FROM activities WHERE id = ?',
        ('activity-1',),
    ).fetchone()
    pipeline = connection.execute(
        'SELECT model_id FROM pipelines WHERE id = ?',
        ('pipeline-1',),
    ).fetchone()
    defaults = connection.execute(
        'SELECT model_id FROM workspace_execution_defaults WHERE workspace_id = ?',
        ('workspace-1',),
    ).fetchone()
    connection.close()

    assert activity is not None
    assert activity[0] == 'gpt-5'
    assert json.loads(activity[1]) == {
        'agents': [
            {
                'model_id': 'gpt-5',
                'persona_id': 'persona-1',
                'role': 'generator',
            }
        ]
    }
    assert pipeline == ('gpt-5',)
    assert defaults == ('gpt-5',)