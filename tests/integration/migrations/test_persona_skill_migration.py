"""Integration coverage for relational persona-skill associations."""

import sqlite3

from tests.integration.migrations.test_instruction_catalog_migration import (
    apply_migrations,
    insert_project,
    insert_project_instruction,
)


def test_deleting_skill_cascades_from_all_personas() -> None:
    """Deleting a skill removes every association without deleting personas."""

    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    apply_migrations(connection)
    insert_project(connection, 'project-1')
    insert_project_instruction(
        connection,
        instruction_id="persona-1",
        instruction_type="persona",
        origin="custom",
        owner_project_id='project-1',
    )
    insert_project_instruction(
        connection,
        instruction_id="persona-2",
        instruction_type="persona",
        origin="custom",
        owner_project_id='project-1',
        name_key="second persona",
    )
    insert_project_instruction(
        connection,
        instruction_id="skill-1",
        instruction_type="skill",
        origin="custom",
        owner_project_id='project-1',
        name_key="associated skill",
    )
    connection.executemany(
        """
        INSERT INTO persona_skills (
            persona_id,
            skill_id,
            position
        )
        VALUES (?, ?, 0)
        """,
        [
            ("persona-1", "skill-1"),
            ("persona-2", "skill-1"),
        ],
    )

    connection.execute(
        "DELETE FROM instructions WHERE id = 'skill-1'"
    )

    assert connection.execute(
        "SELECT COUNT(*) FROM persona_skills"
    ).fetchone() == (0,)
    assert connection.execute(
        """
        SELECT COUNT(*)
        FROM instructions
        WHERE instruction_type = 'persona'
        """
    ).fetchone() == (2,)
