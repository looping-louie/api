"""Effective workspace-library tests for SqliteInstructionRepository."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import src.app.repositories.instruction_repository as repository_module
from src.app.catalogs import InstructionOrigin, load_instruction_catalog
from src.app.repositories.dependency_repository import (
    SqliteDependencyRepository,
)
from src.app.repositories.instruction_repository import (
    SqliteInstructionRepository,
)
from src.app.services.instruction_catalog_synchronizer import (
    InstructionCatalogSynchronizer,
)
from src.app.services.shared.instruction_service import (
    InstructionDocument,
)
from src.app.services.shared.reference_resolver import ResourceReference


MIGRATIONS_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "sqlite"
)
TIMESTAMP = "2026-07-23T12:00:00+00:00"


class AsyncCursorAdapter:
    """Minimal async facade over a sqlite3 cursor."""

    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    async def fetchall(self) -> list[sqlite3.Row]:
        return self._cursor.fetchall()

    async def fetchone(self) -> sqlite3.Row | None:
        return self._cursor.fetchone()

    async def close(self) -> None:
        self._cursor.close()


class AsyncConnectionAdapter:
    """Minimal async facade over a sqlite3 connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @property
    def row_factory(self) -> Any:
        return self._connection.row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        self._connection.row_factory = value

    async def execute(
        self,
        sql: str,
        parameters: Any = (),
    ) -> AsyncCursorAdapter:
        return AsyncCursorAdapter(
            self._connection.execute(sql, parameters)
        )

    async def commit(self) -> None:
        self._connection.commit()

    async def rollback(self) -> None:
        self._connection.rollback()

    async def close(self) -> None:
        self._connection.close()


@pytest.fixture
def library_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    database_path = tmp_path / "library.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        for path in sorted(MIGRATIONS_PATH.glob("*.sql")):
            connection.executescript(
                path.read_text(encoding="utf-8")
            )

        connection.executemany(
            """
            INSERT INTO workspaces (
                id,
                name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    "workspace-1",
                    "Workspace 1",
                    TIMESTAMP,
                    TIMESTAMP,
                ),
                (
                    "workspace-2",
                    "Workspace 2",
                    TIMESTAMP,
                    TIMESTAMP,
                ),
            ],
        )
        insert_custom(
            connection,
            instruction_id="custom-workspace-1",
            workspace_id="workspace-1",
            name="Workspace Needle",
            description="Unique workspace needle description.",
        )
        insert_custom(
            connection,
            instruction_id="custom-workspace-2",
            workspace_id="workspace-2",
            name="Private Other Skill",
            description="Must not leak between workspaces.",
        )
        insert_custom(
            connection,
            instruction_id="custom-percent",
            workspace_id="workspace-1",
            name="100% Coverage",
            description="Literal wildcard search.",
        )
        insert_marketplace(connection)
        connection.execute(
            """
            INSERT INTO workspace_instruction_settings (
                workspace_id,
                instruction_id,
                enabled,
                created_at,
                updated_at
            )
            VALUES (
                'workspace-1',
                'marketplace-skill',
                1,
                ?,
                ?
            )
            """,
            (
                TIMESTAMP,
                TIMESTAMP,
            ),
        )
        connection.commit()

    InstructionCatalogSynchronizer(
        database_path=database_path,
    ).synchronize(
        load_instruction_catalog()
    )

    async def connect(
        database: str | Path,
    ) -> AsyncConnectionAdapter:
        return AsyncConnectionAdapter(
            sqlite3.connect(database)
        )

    monkeypatch.setattr(
        repository_module.aiosqlite,
        "connect",
        connect,
    )
    return database_path


@pytest.mark.asyncio
async def test_workspace_library_combines_visible_origins(
    library_database: Path,
) -> None:
    repository = SqliteInstructionRepository(
        library_database
    )
    workspace_1 = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
    )
    workspace_2 = await repository.list_available_for_workspace(
        workspace_id="workspace-2",
        instruction_type="skill",
    )
    workspace_1_ids = {
        instruction.id
        for instruction in workspace_1
    }
    workspace_2_ids = {
        instruction.id
        for instruction in workspace_2
    }
    marketplace = next(
        instruction
        for instruction in workspace_1
        if instruction.id == "marketplace-skill"
    )
    foreign_custom = (
        await repository.get_available_for_workspace(
            workspace_id="workspace-1",
            instruction_type="skill",
            instruction_id="custom-workspace-2",
        )
    )

    assert "builtin:skill:security" in workspace_1_ids
    assert "custom-workspace-1" in workspace_1_ids
    assert "custom-workspace-2" not in workspace_1_ids
    assert "marketplace-skill" in workspace_1_ids
    assert marketplace.enabled_by_default is False
    assert marketplace.enabled is True
    assert foreign_custom is None

    assert "builtin:skill:security" in workspace_2_ids
    assert "custom-workspace-2" in workspace_2_ids
    assert "custom-workspace-1" not in workspace_2_ids
    assert "marketplace-skill" not in workspace_2_ids


@pytest.mark.asyncio
async def test_builtin_can_be_described_by_workspace(
    library_database: Path,
) -> None:
    repository = SqliteInstructionRepository(
        library_database
    )

    builtin = await repository.get_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id="builtin:skill:security",
    )

    assert builtin is not None
    assert builtin.origin == InstructionOrigin.BUILTIN
    assert builtin.owner_workspace_id is None
    assert builtin.workspace_id == "workspace-1"
    assert builtin.instructions
    assert builtin.metadata
    assert builtin.enabled is builtin.enabled_by_default
    assert builtin.selectable is builtin.enabled


@pytest.mark.asyncio
async def test_explicit_setting_overrides_builtin_default(
    library_database: Path,
) -> None:
    repository = SqliteInstructionRepository(
        library_database
    )
    instruction_id = "builtin:skill:security"

    assert await repository.is_enabled(
        workspace_id="workspace-1",
        instruction_id=instruction_id,
    )
    assert await repository.set_enabled(
        workspace_id="workspace-1",
        instruction_id=instruction_id,
        enabled=False,
    )

    disabled = await repository.get_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id=instruction_id,
    )
    listed = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
    )

    assert disabled is not None
    assert disabled.enabled is False
    assert disabled.selectable is False
    assert await repository.is_enabled(
        workspace_id="workspace-1",
        instruction_id=instruction_id,
    ) is False
    assert instruction_id in {
        instruction.id
        for instruction in listed
    }


@pytest.mark.asyncio
async def test_deprecated_builtin_is_only_resolved_historically(
    library_database: Path,
) -> None:
    repository = SqliteInstructionRepository(
        library_database
    )
    instruction_id = "builtin:skill:security"

    with sqlite3.connect(library_database) as connection:
        connection.execute(
            """
            UPDATE instructions
            SET deprecated = 1
            WHERE id = ?
            """,
            (instruction_id,),
        )
        connection.commit()

    current = await repository.get_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id=instruction_id,
    )
    historical = await repository.get_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id=instruction_id,
        include_deprecated=True,
    )
    current_list = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
    )
    historical_list = (
        await repository.list_available_for_workspace(
            workspace_id="workspace-1",
            instruction_type="skill",
            include_deprecated=True,
        )
    )

    assert current is None
    assert historical is not None
    assert historical.deprecated is True
    assert historical.selectable is False
    assert await repository.is_enabled(
        workspace_id="workspace-1",
        instruction_id=instruction_id,
    ) is False
    assert instruction_id not in {
        instruction.id
        for instruction in current_list
    }
    assert instruction_id in {
        instruction.id
        for instruction in historical_list
    }


@pytest.mark.asyncio
async def test_owned_custom_lookup_is_isolated(
    library_database: Path,
) -> None:
    repository = SqliteInstructionRepository(
        library_database
    )

    owned = await repository.get_owned_custom(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id="custom-workspace-1",
    )
    foreign = await repository.get_owned_custom(
        workspace_id="workspace-2",
        instruction_type="skill",
        instruction_id="custom-workspace-1",
    )
    builtin = await repository.get_owned_custom(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id="builtin:skill:security",
    )
    foreign_override = await repository.set_enabled(
        workspace_id="workspace-2",
        instruction_id="custom-workspace-1",
        enabled=False,
    )

    assert owned is not None
    assert foreign is None
    assert builtin is None
    assert foreign_override is False


@pytest.mark.asyncio
async def test_effective_search_is_literal_and_order_is_stable(
    library_database: Path,
) -> None:
    repository = SqliteInstructionRepository(
        library_database
    )

    literal = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        search="100%",
    )
    description = (
        await repository.list_available_for_workspace(
            workspace_id="workspace-1",
            instruction_type="skill",
            search="  UNIQUE   WORKSPACE needle ",
        )
    )
    all_skills = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
    )

    assert [
        instruction.id
        for instruction in literal
    ] == [
        "custom-percent",
    ]
    assert [
        instruction.id
        for instruction in description
    ] == [
        "custom-workspace-1",
    ]
    ordering = [
        (
            normalize(instruction.name),
            instruction.name.casefold(),
            instruction.id,
        )
        for instruction in all_skills
    ]
    assert ordering == sorted(ordering)


@pytest.mark.asyncio
async def test_custom_persists_source_instruction_id(
    library_database: Path,
) -> None:
    repository = SqliteInstructionRepository(
        library_database
    )
    now = datetime(
        2026,
        7,
        23,
        13,
        0,
        tzinfo=UTC,
    )
    document = InstructionDocument(
        id="forked-security",
        workspace_id="workspace-1",
        instruction_type="skill",
        name="Forked Security",
        description="Editable builtin fork.",
        instructions="Forked instructions.",
        metadata={"forked": True},
        version=1,
        created_at=now,
        updated_at=now,
        source_instruction_id="builtin:skill:security",
    )

    await repository.create(document)
    stored = await repository.get_owned_custom(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id=document.id,
    )
    available = await repository.get_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id=document.id,
    )
    summaries = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
    )
    summary = next(
        item
        for item in summaries
        if item.id == document.id
    )

    assert stored == document
    assert available is not None
    assert available.origin == InstructionOrigin.CUSTOM
    assert available.source_instruction_id == (
        "builtin:skill:security"
    )
    assert summary.source_instruction_id == (
        "builtin:skill:security"
    )


@pytest.mark.asyncio
async def test_builtin_dependencies_are_scoped_by_referencing_workspace(
    library_database: Path,
) -> None:
    with sqlite3.connect(library_database) as connection:
        for workspace_id, council_id in (
            ("workspace-1", "council-1"),
            ("workspace-2", "council-2"),
        ):
            connection.execute(
                """
                INSERT INTO compositions (
                    id,
                    workspace_id,
                    composition_type,
                    name,
                    name_key,
                    description,
                    attributes_json,
                    version,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, 'council', ?, ?, '', '{}', 1, ?, ?)
                """,
                (
                    council_id,
                    workspace_id,
                    council_id,
                    council_id,
                    TIMESTAMP,
                    TIMESTAMP,
                ),
            )
            connection.execute(
                """
                INSERT INTO resource_dependencies (
                    workspace_id,
                    source_type,
                    source_id,
                    target_type,
                    target_id,
                    relation,
                    position
                )
                VALUES (?, 'council', ?, 'skill', ?, ?, 0)
                """,
                (
                    workspace_id,
                    council_id,
                    "builtin:skill:security",
                    "assignment_skill",
                ),
            )

    repository = SqliteDependencyRepository(library_database)
    target = ResourceReference(
        resource_type="skill",
        resource_id="builtin:skill:security",
    )
    workspace_one = await repository.find_usages(
        workspace_id="workspace-1",
        target=target,
    )
    workspace_two = await repository.find_usages(
        workspace_id="workspace-2",
        target=target,
    )

    assert [usage.source.resource_id for usage in workspace_one] == [
        "council-1",
    ]
    assert [usage.source.resource_id for usage in workspace_two] == [
        "council-2",
    ]


def insert_custom(
    connection: sqlite3.Connection,
    *,
    instruction_id: str,
    workspace_id: str,
    name: str,
    description: str,
) -> None:
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
        VALUES (?, 'skill', 'custom', ?, ?, ?, ?, ?, '{}', 1, 0, 1, ?, ?)
        """,
        (
            instruction_id,
            workspace_id,
            name,
            normalize(name),
            description,
            f"Instructions for {name}.",
            TIMESTAMP,
            TIMESTAMP,
        ),
    )


def insert_marketplace(
    connection: sqlite3.Connection,
) -> None:
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
            catalog_version,
            checksum,
            enabled_by_default,
            deprecated,
            version,
            created_at,
            updated_at
        )
        VALUES (
            'marketplace-skill',
            'skill',
            'marketplace',
            NULL,
            'Marketplace Skill',
            'marketplace skill',
            'Authorized marketplace content.',
            'Marketplace instructions.',
            '{}',
            1,
            ?,
            0,
            0,
            1,
            ?,
            ?
        )
        """,
        (
            "f" * 64,
            TIMESTAMP,
            TIMESTAMP,
        ),
    )


def normalize(value: str) -> str:
    return " ".join(
        value.strip().casefold().split()
    )
