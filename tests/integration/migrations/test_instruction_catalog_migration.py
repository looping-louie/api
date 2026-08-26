"""Migration coverage for global and workspace instruction definitions."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


SQLITE_MIGRATIONS = (
    Path(__file__).resolve().parents[3]
    / "migrations"
    / "sqlite"
)
EXPECTED_INSTRUCTION_COLUMNS = [
    "id",
    "instruction_type",
    "origin",
    "owner_user_id",
    "owner_workspace_id",
    "source_instruction_id",
    "name",
    "name_key",
    "description",
    "content",
    "metadata_json",
    "catalog_version",
    "checksum",
    "enabled_by_default",
    "deprecated",
    "version",
    "created_at",
    "updated_at",
]


def apply_migrations(
    connection: sqlite3.Connection,
    *,
    through: str | None = None,
) -> None:
    """Apply repository SQLite migrations in order."""

    for path in sorted(SQLITE_MIGRATIONS.glob("*.sql")):
        connection.executescript(
            path.read_text(encoding="utf-8")
        )

        if path.stem == through:
            break


def insert_workspace(
    connection: sqlite3.Connection,
    workspace_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO workspaces (
            id,
            name,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            workspace_id,
            workspace_id,
            "2026-07-23T10:00:00+00:00",
            "2026-07-23T10:00:00+00:00",
        ),
    )
    users_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'",
    ).fetchone()
    if users_exists is not None:
        user_id = f'user-{workspace_id}'
        connection.execute(
            '''
            INSERT INTO users (id, created_at, updated_at)
            VALUES (?, ?, ?)
            ''',
            (user_id, '2026-07-23T10:00:00+00:00', '2026-07-23T10:00:00+00:00'),
        )
        connection.execute(
            '''
            INSERT INTO workspace_memberships (
                workspace_id, user_id, role, is_default, created_at
            ) VALUES (?, ?, 'owner', 1, ?)
            ''',
            (workspace_id, user_id, '2026-07-23T10:00:00+00:00'),
        )


def test_empty_database_has_catalog_instruction_schema() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    apply_migrations(connection)

    columns = [
        str(row[1])
        for row in connection.execute(
            "PRAGMA table_info(instructions)"
        )
    ]
    setting_columns = [
        str(row[1])
        for row in connection.execute(
            "PRAGMA table_info(workspace_instruction_settings)"
        )
    ]

    assert columns == EXPECTED_INSTRUCTION_COLUMNS
    assert setting_columns == [
        "workspace_id",
        "instruction_id",
        "enabled",
        "created_at",
        "updated_at",
    ]
    assert "content" not in setting_columns


def test_existing_instruction_is_preserved_as_custom() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    apply_migrations(
        connection,
        through="0004_provider_credentials",
    )
    insert_workspace(connection, "workspace-1")
    connection.execute(
        """
        INSERT INTO instructions (
            id,
            workspace_id,
            instruction_type,
            name,
            name_key,
            description,
            content,
            metadata_json,
            version,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "existing-skill",
            "workspace-1",
            "skill",
            "Existing Skill",
            "existing skill",
            "Existing description.",
            "Existing content.",
            '{"category":"existing"}',
            3,
            "2026-07-20T10:00:00+00:00",
            "2026-07-21T10:00:00+00:00",
        ),
    )
    connection.commit()

    connection.executescript(
        (
            SQLITE_MIGRATIONS
            / "0005_instruction_catalog.sql"
        ).read_text(encoding="utf-8")
    )
    row = connection.execute(
        """
        SELECT *
        FROM instructions
        WHERE id = 'existing-skill'
        """
    ).fetchone()

    assert row is not None
    assert row["origin"] == "custom"
    assert row["owner_workspace_id"] == "workspace-1"
    assert row["source_instruction_id"] is None
    assert row["content"] == "Existing content."
    assert row["metadata_json"] == '{"category":"existing"}'
    assert row["catalog_version"] is None
    assert row["checksum"] is None
    assert row["enabled_by_default"] == 1
    assert row["deprecated"] == 0
    assert row["version"] == 3


def test_user_ownership_migration_uses_the_earliest_workspace_owner() -> None:
    """Legacy custom definitions receive a deterministic User owner."""

    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0046_users')
    insert_workspace(connection, 'workspace-1')
    connection.execute(
        '''
        INSERT INTO users (id, created_at, updated_at)
        VALUES ('user-earlier', '2026-07-22T10:00:00+00:00', '2026-07-22T10:00:00+00:00')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO workspace_memberships (
            workspace_id, user_id, role, is_default, created_at
        ) VALUES ('workspace-1', 'user-earlier', 'owner', 0, '2026-07-22T10:00:00+00:00')
        ''',
    )
    insert_instruction(
        connection,
        instruction_id='legacy-skill',
        origin='custom',
        owner_workspace_id='workspace-1',
    )
    connection.executescript(
        (SQLITE_MIGRATIONS / '0047_user_owned_instructions.sql').read_text(
            encoding='utf-8',
        ),
    )

    owner = connection.execute(
        "SELECT owner_user_id FROM instructions WHERE id = 'legacy-skill'",
    ).fetchone()

    assert owner is not None
    assert owner['owner_user_id'] == 'user-earlier'


def test_origin_ownership_and_version_checks_are_enforced() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    apply_migrations(connection)
    insert_workspace(connection, "workspace-1")

    insert_instruction(
        connection,
        instruction_id="legacy-ownerless-custom",
        origin="custom",
        owner_workspace_id=None,
    )

    with pytest.raises(sqlite3.IntegrityError):
        insert_instruction(
            connection,
            instruction_id="owned-builtin",
            origin="builtin",
            owner_workspace_id="workspace-1",
            catalog_version=1,
            checksum="a" * 64,
        )

    with pytest.raises(sqlite3.IntegrityError):
        insert_instruction(
            connection,
            instruction_id="unversioned-builtin",
            origin="builtin",
            owner_workspace_id=None,
            checksum="a" * 64,
        )

    with pytest.raises(sqlite3.IntegrityError):
        insert_instruction(
            connection,
            instruction_id="unchecked-builtin",
            origin="builtin",
            owner_workspace_id=None,
            catalog_version=1,
        )

    insert_instruction(
        connection,
        instruction_id="builtin:skill:security",
        origin="builtin",
        owner_workspace_id=None,
        catalog_version=1,
        checksum="a" * 64,
    )

    assert connection.execute(
        """
        SELECT owner_workspace_id
        FROM instructions
        WHERE id = 'builtin:skill:security'
        """
    ).fetchone() == (None,)


def test_partial_unique_indexes_scope_names_by_origin() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    apply_migrations(connection)
    insert_workspace(connection, "workspace-1")
    insert_workspace(connection, "workspace-2")

    insert_instruction(
        connection,
        instruction_id="builtin:skill:review",
        origin="builtin",
        owner_workspace_id=None,
        catalog_version=1,
        checksum="b" * 64,
        name_key="review",
    )
    insert_instruction(
        connection,
        instruction_id="custom-1",
        origin="custom",
        owner_workspace_id="workspace-1",
        name_key="review",
    )
    insert_instruction(
        connection,
        instruction_id="custom-2",
        origin="custom",
        owner_workspace_id="workspace-2",
        name_key="review",
    )

    with pytest.raises(sqlite3.IntegrityError):
        insert_instruction(
            connection,
            instruction_id="duplicate-builtin",
            origin="builtin",
            owner_workspace_id=None,
            catalog_version=1,
            checksum="c" * 64,
            name_key="review",
        )

    with pytest.raises(sqlite3.IntegrityError):
        insert_instruction(
            connection,
            instruction_id="duplicate-custom",
            origin="custom",
            owner_workspace_id="workspace-1",
            name_key="review",
        )


@pytest.mark.parametrize(
    ("enabled_by_default", "deprecated", "version"),
    [
        (2, 0, 1),
        (1, -1, 1),
        (1, 0, 0),
    ],
)
def test_boolean_and_resource_version_checks_are_enforced(
    enabled_by_default: int,
    deprecated: int,
    version: int,
) -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    apply_migrations(connection)
    insert_workspace(connection, "workspace-1")

    with pytest.raises(sqlite3.IntegrityError):
        insert_instruction(
            connection,
            instruction_id="invalid-custom",
            origin="custom",
            owner_workspace_id="workspace-1",
            enabled_by_default=enabled_by_default,
            deprecated=deprecated,
            version=version,
        )


def test_workspace_settings_reference_content_without_copying_it() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    apply_migrations(connection)
    insert_workspace(connection, "workspace-1")
    insert_instruction(
        connection,
        instruction_id="builtin:persona:tech_lead",
        instruction_type="persona",
        origin="builtin",
        owner_workspace_id=None,
        catalog_version=1,
        checksum="d" * 64,
    )
    timestamp = "2026-07-23T10:00:00+00:00"
    connection.execute(
        """
        INSERT INTO workspace_instruction_settings (
            workspace_id,
            instruction_id,
            enabled,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "workspace-1",
            "builtin:persona:tech_lead",
            1,
            timestamp,
            timestamp,
        ),
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO workspace_instruction_settings (
                workspace_id,
                instruction_id,
                enabled,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "workspace-1",
                "builtin:persona:tech_lead",
                0,
                timestamp,
                timestamp,
            ),
        )


def insert_instruction(
    connection: sqlite3.Connection,
    *,
    instruction_id: str,
    origin: str,
    owner_workspace_id: str | None,
    owner_user_id: str | None = None,
    instruction_type: str = "skill",
    name_key: str = "catalog entry",
    catalog_version: int | None = None,
    checksum: str | None = None,
    enabled_by_default: int = 1,
    deprecated: int = 0,
    version: int = 1,
) -> None:
    has_owner_user_id = any(
        row[1] == 'owner_user_id'
        for row
        in connection.execute('PRAGMA table_info(instructions)')
    )
    resolved_owner_user_id = (
        owner_user_id
        if owner_user_id is not None
        else (
            f'user-{owner_workspace_id}'
            if origin == 'custom' and owner_workspace_id is not None
            else None
        )
    )
    if not has_owner_user_id:
        connection.execute(
            '''
            INSERT INTO instructions (
                id, instruction_type, origin, owner_workspace_id,
                source_instruction_id, name, name_key, description, content,
                metadata_json, catalog_version, checksum, enabled_by_default,
                deprecated, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, ?, ?, '', ?, '{}', ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                instruction_id,
                instruction_type,
                origin,
                owner_workspace_id,
                name_key.title(),
                name_key,
                'Content.',
                catalog_version,
                checksum,
                enabled_by_default,
                deprecated,
                version,
                '2026-07-23T10:00:00+00:00',
                '2026-07-23T10:00:00+00:00',
            ),
        )
        return
    connection.execute(
        """
        INSERT INTO instructions (
            id,
            instruction_type,
            origin,
            owner_user_id,
            owner_workspace_id,
            source_instruction_id,
            name,
            name_key,
            description,
            content,
            metadata_json,
            catalog_version,
            checksum,
            enabled_by_default,
            deprecated,
            version,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, NULL, ?, ?, '', ?, '{}', ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            instruction_id,
            instruction_type,
            origin,
            resolved_owner_user_id,
            owner_workspace_id,
            name_key.title(),
            name_key,
            "Content.",
            catalog_version,
            checksum,
            enabled_by_default,
            deprecated,
            version,
            "2026-07-23T10:00:00+00:00",
            "2026-07-23T10:00:00+00:00",
        ),
    )
