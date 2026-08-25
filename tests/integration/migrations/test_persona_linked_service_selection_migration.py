"""Integration coverage for persona linked-service selection constraints."""

import sqlite3

from tests.integration.migrations.test_instruction_catalog_migration import (
    SQLITE_MIGRATIONS,
    apply_migrations,
    insert_instruction,
    insert_workspace,
)


def test_forward_migration_drops_persona_linked_service_selections() -> None:
    """The forward migration removes the retired Persona routing table."""

    connection = sqlite3.connect(':memory:')
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0044_execution_overrides')
    insert_workspace(connection, 'workspace-1')
    insert_instruction(
        connection,
        instruction_id='persona-1',
        instruction_type='persona',
        origin='custom',
        owner_workspace_id='workspace-1',
    )
    connection.execute(
        '''
        INSERT INTO linked_services (
            id, workspace_id, name, provider_type, created_at, updated_at
        ) VALUES ('linked-service-1', 'workspace-1', 'primary', 'openai', 'now', 'now')
        '''
    )
    connection.execute(
        '''
        INSERT INTO persona_linked_service_selections (
            workspace_id, persona_id, linked_service_id, model_id
        ) VALUES ('workspace-1', 'persona-1', 'linked-service-1', 'model-1')
        '''
    )
    connection.execute(
        '''
        INSERT INTO activities (
            id, workspace_id, name, description, status, activity_type, config_json,
            created_at, created_by, updated_at, updated_by
        ) VALUES (
            'activity-1', 'workspace-1', 'Implementation', '', 'active',
            'direct_loop',
            '{"agents":[{"model_id":"legacy-model","persona_id":"persona-1","role":"generator"}]}',
            'now', 'user-1', 'now', 'user-1'
        )
        '''
    )

    connection.executescript(
        (
            SQLITE_MIGRATIONS
            / '0045_remove_persona_linked_service_selections.sql'
        ).read_text(encoding='utf-8')
    )

    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name = 'persona_linked_service_selections'"
    ).fetchone() is None
    config_json = connection.execute(
        "SELECT config_json FROM activities WHERE id = 'activity-1'"
    ).fetchone()[0]
    assert config_json == (
        '{"agents":[{"persona_id":"persona-1","role":"generator",'
        '"model_target":{"linked_service_id":"linked-service-1",'
        '"model_id":"model-1"}}]}'
    )
