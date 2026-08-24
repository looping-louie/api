"""Tests for effective instruction reference availability."""

from datetime import UTC, datetime

import pytest

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.repositories.shared.reference_repository import (
    CompositeReferenceRepository,
)
from src.app.services.persona_skills import (
    AvailableDefinitionDocument,
    DefinitionDocument,
)
from tests.fakes.instruction_repository import FakeInstructionRepository


class FakeModelCatalog:
    """Minimal model lookup required by CompositeReferenceRepository."""

    def get_many(
        self,
        *,
        model_ids: tuple[str, ...],
    ) -> dict[str, object]:
        """Return no models for instruction-only tests."""

        del model_ids
        return {}


def build_repository(
    instruction_repository: FakeInstructionRepository,
) -> CompositeReferenceRepository:
    """Build an instruction-backed composite repository."""

    return CompositeReferenceRepository(
        instruction_repository=instruction_repository,
        model_catalog_service=FakeModelCatalog(),  # type: ignore[arg-type]
    )


def build_builtin(
    *,
    instruction_id: str,
    deprecated: bool = False,
) -> AvailableDefinitionDocument:
    """Build one builtin skill definition."""

    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    return AvailableDefinitionDocument(
        id=instruction_id,
        workspace_id="catalog",
        instruction_type="skill",
        origin=InstructionOrigin.BUILTIN,
        owner_workspace_id=None,
        source_instruction_id=None,
        name="Security",
        description="Security checks.",
        instructions="Review security.",
        metadata={},
        enabled=True,
        enabled_by_default=True,
        deprecated=deprecated,
        catalog_version=1,
        checksum="a" * 64,
        version=1,
        created_at=now,
        updated_at=now,
    )


def build_custom(
    *,
    instruction_id: str,
    workspace_id: str,
) -> DefinitionDocument:
    """Build one workspace-owned skill definition."""

    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    return DefinitionDocument(
        id=instruction_id,
        workspace_id=workspace_id,
        instruction_type="skill",
        name="Custom security",
        description="Workspace checks.",
        instructions="Review custom security.",
        metadata={},
        version=1,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_effective_reference_lookup_enforces_workspace_and_selection(
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Only selectable instructions in the workspace can be referenced."""

    builtin = build_builtin(
        instruction_id="builtin:skill:security",
    )
    deprecated = build_builtin(
        instruction_id="builtin:skill:retired",
        deprecated=True,
    )
    instruction_repository.seed_available(builtin)
    instruction_repository.seed_available(deprecated)
    own_custom = build_custom(
        instruction_id="custom-own",
        workspace_id="workspace-1",
    )
    other_custom = build_custom(
        instruction_id="custom-other",
        workspace_id="workspace-2",
    )
    await instruction_repository.create(document=own_custom)
    await instruction_repository.create(document=other_custom)
    repository = build_repository(instruction_repository)

    available = await repository.get_many(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_ids=[
            builtin.id,
            deprecated.id,
            own_custom.id,
            other_custom.id,
        ],
    )

    assert set(available) == {
        builtin.id,
        own_custom.id,
    }

    await instruction_repository.set_enabled(
        workspace_id="workspace-1",
        instruction_id=builtin.id,
        enabled=False,
    )
    selectable = await repository.get_many(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_ids=[builtin.id],
    )

    assert selectable == {}
