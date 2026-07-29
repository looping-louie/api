"""Tests for transactional builtin catalog synchronization."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.app.catalogs import load_instruction_catalog
from src.app.catalogs.loader import InstructionCatalog
from src.app.services.shared.instruction_catalog_synchronizer import (
    CatalogChecksumConflictError,
    CatalogChecksumPolicy,
    CatalogVersionRegressionError,
    InstructionCatalogSynchronizer,
)


MIGRATIONS_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "sqlite"
)
FIXED_NOW = datetime(
    2026,
    7,
    23,
    12,
    0,
    tzinfo=UTC,
)


@pytest.fixture
def catalog_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "catalog.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        for path in sorted(MIGRATIONS_PATH.glob("*.sql")):
            connection.executescript(
                path.read_text(encoding="utf-8")
            )

    return database_path


def build_synchronizer(
    database_path: Path,
    *,
    policy: CatalogChecksumPolicy = (
        CatalogChecksumPolicy.ALLOW_WITH_WARNING
    ),
) -> InstructionCatalogSynchronizer:
    return InstructionCatalogSynchronizer(
        database_path=database_path,
        checksum_policy=policy,
        clock=lambda: FIXED_NOW,
    )


def replace_skill(
    catalog: InstructionCatalog,
    position: int,
    **changes: object,
) -> InstructionCatalog:
    skills = list(catalog.skills)
    skills[position] = replace(
        skills[position],
        **changes,
    )
    return InstructionCatalog(
        skills=tuple(skills),
        personas=catalog.personas,
    )


def test_synchronization_is_idempotent(
    catalog_database: Path,
) -> None:
    catalog = load_instruction_catalog()
    synchronizer = build_synchronizer(catalog_database)

    first = synchronizer.synchronize(catalog)
    second = synchronizer.synchronize(catalog)

    with sqlite3.connect(catalog_database) as connection:
        rows = connection.execute(
            """
            SELECT id, owner_workspace_id
            FROM instructions
            WHERE origin = 'builtin'
            """
        ).fetchall()

    assert first.inserted == len(catalog.entries)
    assert first.updated == 0
    assert second.inserted == 0
    assert second.updated == 0
    assert second.unchanged == len(catalog.entries)
    assert len(rows) == len(catalog.entries)
    assert all(owner_workspace_id is None for _, owner_workspace_id in rows)


def test_synchronization_persists_persona_skill_associations(
    catalog_database: Path,
) -> None:
    """Catalog synchronization stores ordered associations relationally."""

    catalog = load_instruction_catalog()
    persona = catalog.personas[0]

    build_synchronizer(catalog_database).synchronize(catalog)

    with sqlite3.connect(catalog_database) as connection:
        skill_ids = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT skill_id
                FROM persona_skills
                WHERE persona_id = ?
                ORDER BY position ASC
                """,
                (persona.id,),
            )
        ]

    assert skill_ids == list(persona.skill_ids)


def test_synchronization_does_not_modify_custom_instructions(
    catalog_database: Path,
) -> None:
    timestamp = FIXED_NOW.isoformat()

    with sqlite3.connect(catalog_database) as connection:
        connection.execute(
            """
            INSERT INTO workspaces (
                id,
                name,
                created_at,
                updated_at
            )
            VALUES ('workspace-1', 'Workspace', ?, ?)
            """,
            (
                timestamp,
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO instructions (
                id,
                instruction_type,
                origin,
                owner_workspace_id,
                name,
                name_key,
                description,
                content,
                metadata_json,
                enabled_by_default,
                deprecated,
                version,
                created_at,
                updated_at
            )
            VALUES (
                'custom-security',
                'skill',
                'custom',
                'workspace-1',
                'Security',
                'security',
                'Custom description',
                'Custom content',
                '{"custom":true}',
                1,
                0,
                4,
                ?,
                ?
            )
            """,
            (
                timestamp,
                timestamp,
            ),
        )
        connection.commit()

    build_synchronizer(catalog_database).synchronize(
        load_instruction_catalog()
    )

    with sqlite3.connect(catalog_database) as connection:
        custom = connection.execute(
            """
            SELECT
                origin,
                owner_workspace_id,
                content,
                metadata_json,
                version
            FROM instructions
            WHERE id = 'custom-security'
            """
        ).fetchone()

    assert custom == (
        "custom",
        "workspace-1",
        "Custom content",
        '{"custom":true}',
        4,
    )


def test_removed_builtin_is_deprecated_but_not_deleted(
    catalog_database: Path,
) -> None:
    catalog = load_instruction_catalog()
    removed = catalog.skills[0]
    reduced = InstructionCatalog(
        skills=catalog.skills[1:],
        personas=catalog.personas,
    )
    synchronizer = build_synchronizer(catalog_database)
    synchronizer.synchronize(catalog)

    first = synchronizer.synchronize(reduced)
    second = synchronizer.synchronize(reduced)

    with sqlite3.connect(catalog_database) as connection:
        row = connection.execute(
            """
            SELECT deprecated, version
            FROM instructions
            WHERE id = ?
            """,
            (removed.id,),
        ).fetchone()
        total = connection.execute(
            """
            SELECT COUNT(*)
            FROM instructions
            WHERE origin = 'builtin'
            """
        ).fetchone()

    assert first.deprecated == 1
    assert second.deprecated == 0
    assert row == (1, 2)
    assert total == (len(catalog.entries),)


def test_higher_catalog_version_updates_stable_id(
    catalog_database: Path,
) -> None:
    catalog = load_instruction_catalog()
    original = catalog.skills[0]
    assert original.catalog_version is not None
    changed = replace_skill(
        catalog,
        0,
        instructions=f"{original.instructions}\nChanged.\n",
        checksum="e" * 64,
        catalog_version=original.catalog_version + 1,
    )
    synchronizer = build_synchronizer(catalog_database)
    synchronizer.synchronize(catalog)

    result = synchronizer.synchronize(changed)

    with sqlite3.connect(catalog_database) as connection:
        row = connection.execute(
            """
            SELECT id, catalog_version, checksum, version
            FROM instructions
            WHERE id = ?
            """,
            (original.id,),
        ).fetchone()

    assert result.updated == 1
    assert row == (
        original.id,
        original.catalog_version + 1,
        "e" * 64,
        2,
    )


def test_catalog_version_cannot_regress(
    catalog_database: Path,
) -> None:
    catalog = load_instruction_catalog()
    entry = catalog.skills[0]
    assert entry.catalog_version is not None
    synchronizer = build_synchronizer(catalog_database)
    synchronizer.synchronize(catalog)

    with sqlite3.connect(catalog_database) as connection:
        connection.execute(
            """
            UPDATE instructions
            SET catalog_version = ?
            WHERE id = ?
            """,
            (
                entry.catalog_version + 1,
                entry.id,
            ),
        )
        connection.commit()

    with pytest.raises(
        CatalogVersionRegressionError,
        match="cannot decrease",
    ):
        synchronizer.synchronize(catalog)


def test_development_policy_warns_and_updates_checksum(
    catalog_database: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    catalog = load_instruction_catalog()
    changed = replace_skill(
        catalog,
        0,
        checksum="a" * 64,
    )
    synchronizer = build_synchronizer(catalog_database)
    synchronizer.synchronize(catalog)

    with caplog.at_level(logging.WARNING):
        result = synchronizer.synchronize(changed)

    assert result.updated == 1
    assert "without incrementing catalog_version" in caplog.text
    assert "development policy" in caplog.text


def test_strict_policy_rejects_unversioned_checksum_change(
    catalog_database: Path,
) -> None:
    catalog = load_instruction_catalog()
    entry = catalog.skills[0]
    changed = replace_skill(
        catalog,
        0,
        checksum="b" * 64,
    )
    development = build_synchronizer(catalog_database)
    development.synchronize(catalog)
    strict = build_synchronizer(
        catalog_database,
        policy=(
            CatalogChecksumPolicy.REQUIRE_VERSION_INCREMENT
        ),
    )

    with pytest.raises(
        CatalogChecksumConflictError,
        match="without incrementing catalog_version",
    ):
        strict.synchronize(changed)

    with sqlite3.connect(catalog_database) as connection:
        checksum = connection.execute(
            """
            SELECT checksum
            FROM instructions
            WHERE id = ?
            """,
            (entry.id,),
        ).fetchone()

    assert checksum == (entry.checksum,)


def test_database_failure_rolls_back_every_update(
    catalog_database: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    catalog = load_instruction_catalog()
    first = catalog.skills[0]
    second = catalog.skills[1]
    changed = replace_skill(
        replace_skill(
            catalog,
            0,
            checksum="c" * 64,
        ),
        1,
        checksum="d" * 64,
    )
    synchronizer = build_synchronizer(catalog_database)
    synchronizer.synchronize(catalog)

    with sqlite3.connect(catalog_database) as connection:
        connection.execute(
            f"""
            CREATE TRIGGER reject_second_builtin_update
            BEFORE UPDATE ON instructions
            WHEN NEW.id = '{second.id}'
            BEGIN
                SELECT RAISE(ABORT, 'forced synchronization failure');
            END
            """
        )
        connection.commit()

    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(
            sqlite3.IntegrityError,
            match="forced synchronization failure",
        ),
    ):
        synchronizer.synchronize(changed)

    with sqlite3.connect(catalog_database) as connection:
        rows = connection.execute(
            """
            SELECT id, checksum, version
            FROM instructions
            WHERE id IN (?, ?)
            ORDER BY id
            """,
            (
                first.id,
                second.id,
            ),
        ).fetchall()

    expected = sorted(
        [
            (
                first.id,
                first.checksum,
                1,
            ),
            (
                second.id,
                second.checksum,
                1,
            ),
        ]
    )
    assert rows == expected
    assert caplog.text == ""
