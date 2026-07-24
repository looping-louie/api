"""Tests for effective instruction reference availability."""

from datetime import UTC, datetime

import pytest

from src.app.catalogs.instructions import InstructionOrigin
from src.app.repositories.reference_repository import (
    CompositeReferenceRepository,
)
from src.app.services.shared.instruction_service import (
    AvailableInstructionDocument,
    InstructionDocument,
)
from tests.fakes.instruction_repository import FakeInstructionRepository


class UnusedModelCatalog:
    """Minimal model lookup required by CompositeReferenceRepository."""

    def get_many(
        self,
        *,
        model_ids: tuple[str, ...],
    ) -> dict[str, object]:
        del model_ids
        return {}


def build_repository(
    instruction_repository: FakeInstructionRepository,
) -> CompositeReferenceRepository:
    return CompositeReferenceRepository(
        instruction_repository=instruction_repository,
        model_catalog_service=UnusedModelCatalog(),  # type: ignore[arg-type]
    )


def build_builtin(
    *,
    instruction_id: str,
    deprecated: bool = False,
) -> AvailableInstructionDocument:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    return AvailableInstructionDocument(
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
) -> InstructionDocument:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    return InstructionDocument(
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
    historical = await repository.get_many(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_ids=[builtin.id, deprecated.id],
        include_historical=True,
    )

    assert selectable == {}
    assert set(historical) == {
        builtin.id,
        deprecated.id,
    }
