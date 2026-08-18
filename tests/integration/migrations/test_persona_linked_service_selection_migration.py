"""Integration coverage for persona linked-service selection constraints."""

import sqlite3

import pytest

from tests.integration.migrations.test_instruction_catalog_migration import (
    apply_migrations,
    insert_instruction,
    insert_workspace,
)


def test_linked_service_selection_cascades_with_persona_and_blocks_service_delete() -> None:
    """Selections retain personas while preventing linked-service deletion."""

    connection = sqlite3.connect(':memory:')
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection)
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
            persona_id, linked_service_id, model_id
        ) VALUES ('persona-1', 'linked-service-1', 'model-1')
        '''
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("DELETE FROM linked_services WHERE id = 'linked-service-1'")

    connection.execute("DELETE FROM instructions WHERE id = 'persona-1'")
    assert connection.execute(
        'SELECT COUNT(*) FROM persona_linked_service_selections'
    ).fetchone() == (0,)