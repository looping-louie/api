"""Focused instruction persistence and runtime source tests."""

from datetime import UTC, datetime
from pathlib import Path
import sqlite3

import pytest

from src.app.catalogs import InstructionOrigin
from src.app.repositories.instructions.repository import (
    SqliteInstructionRepository,
)
from src.app.repositories.instructions.persona_skill_repository import (
    SqlitePersonaSkillRepository,
)
from src.app.services.execution_instructions import (
    ExecutionInstructionLibraryService,
)
from src.app.services.persona_skills import InstructionDocument
from src.app.services.shared.tenant import (
    TenantService,
    WorkspaceMembership,
)
from tests.fakes.tenant_repository import FakeTenantRepository
from tests.integration.repositories.instructions.test_availability import (
    TIMESTAMP,
    library_database,
)


@pytest.mark.asyncio
async def test_custom_persists_source_instruction_id(
    library_database: Path,
) -> None:
    """A custom fork retains its builtin source through every query shape."""

    repository = SqliteInstructionRepository(library_database)
    now = datetime(2026, 7, 23, 13, 0, tzinfo=UTC)
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
    summary = next(item for item in summaries if item.id == document.id)

    assert stored == document
    assert available is not None
    assert available.origin == InstructionOrigin.CUSTOM
    assert available.source_instruction_id == "builtin:skill:security"
    assert summary.source_instruction_id == "builtin:skill:security"


@pytest.mark.asyncio
async def test_execution_library_reads_sql_not_packaged_markdown(
    library_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime content comes from synchronized SQL rather than source files."""

    import src.app.catalogs.skills.loader as skill_loader

    service = ExecutionInstructionLibraryService(
        repository=SqliteInstructionRepository(library_database),
        persona_skill_repository=SqlitePersonaSkillRepository(
            library_database,
        ),
        tenant_service=TenantService(
            repository=FakeTenantRepository(
                [
                    WorkspaceMembership(
                        user_id="user-1",
                        workspace_id="workspace-1",
                        is_default=True,
                    ),
                ]
            )
        ),
    )
    initial = await service.load(user_id="user-1")
    initial_content = initial.skill_contents(["security"])[0]
    monkeypatch.setattr(
        skill_loader,
        "load_skill_catalog",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Runtime must not load the packaged catalog")
        ),
    )
    unchanged = await service.load(user_id="user-1")

    with sqlite3.connect(library_database) as connection:
        connection.execute(
            """
            UPDATE instructions
            SET content = ?, version = version + 1, updated_at = ?
            WHERE id = 'builtin:skill:security'
            """,
            ("Runtime content updated directly in SQL.", TIMESTAMP),
        )
    updated = await service.load(user_id="user-1")

    assert unchanged.skill_contents(["security"])[0] == initial_content
    assert updated.skill_contents(["security"]) == [
        "Runtime content updated directly in SQL."
    ]
