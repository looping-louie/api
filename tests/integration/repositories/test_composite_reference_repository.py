"""Integration tests for CompositeReferenceRepository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from src.app.repositories.composition_repository import (
    SqliteCompositionRepository,
)
from src.app.repositories.instruction_repository import (
    SqliteInstructionRepository,
)
from src.app.repositories.provider_repository import (
    SqliteProviderRepository,
)
from src.app.repositories.provider_state_repository import (
    ProviderStateRepositoryAdapter,
)
from src.app.repositories.reference_repository import (
    CompositeReferenceRepository,
)
from src.app.repositories.sqlite_database import SqliteDatabase
from src.app.repositories.tenant_repository import (
    SqliteTenantRepository,
)
from src.app.services.model_service import (
    ModelAvailabilityService,
    ModelCatalogService,
)
from src.app.services.shared.tenant_service import TenantService
from tests.integration.factories import (
    build_composition,
    build_instruction,
)


WorkspaceFactory = Callable[..., Awaitable[None]]


def build_repository(
    *,
    database_path: Path,
    database: SqliteDatabase,
) -> CompositeReferenceRepository:
    """Build the real reference adapter and its dependencies."""

    instruction_repository = SqliteInstructionRepository(
        database_path,
    )
    composition_repository = SqliteCompositionRepository(
        database_path,
    )
    provider_repository = SqliteProviderRepository(
        database,
    )
    provider_state_repository = ProviderStateRepositoryAdapter(
        provider_repository=provider_repository,
    )
    availability_service = ModelAvailabilityService(
        provider_state_repository=provider_state_repository,
    )
    tenant_service = TenantService(
        repository=SqliteTenantRepository(
            database_path,
        ),
    )
    catalog_service = ModelCatalogService(
        tenant_service=tenant_service,
        availability_service=availability_service,
    )

    return CompositeReferenceRepository(
        instruction_repository=instruction_repository,
        composition_repository=composition_repository,
        model_catalog_service=catalog_service,
    )


@pytest.mark.asyncio
async def test_resolves_instruction_and_composition_references(
    sqlite_database_path: Path,
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    instruction_repository = SqliteInstructionRepository(
        sqlite_database_path,
    )
    composition_repository = SqliteCompositionRepository(
        sqlite_database_path,
    )

    await instruction_repository.create(
        build_instruction(
            instruction_id="persona-1",
        )
    )
    await composition_repository.create(
        build_composition(
            composition_id="council-1",
        )
    )

    repository = build_repository(
        database_path=sqlite_database_path,
        database=sqlite_database,
    )

    personas = await repository.get_many(
        workspace_id="workspace-1",
        resource_type="persona",
        resource_ids=[
            "persona-1",
            "missing-persona",
        ],
    )
    councils = await repository.get_many(
        workspace_id="workspace-1",
        resource_type="council",
        resource_ids=[
            "council-1",
        ],
    )

    assert list(personas) == [
        "persona-1",
    ]
    assert personas["persona-1"].name == "Security Reviewer"

    assert list(councils) == [
        "council-1",
    ]
    assert councils["council-1"].name == "Security Council"


@pytest.mark.asyncio
async def test_resolves_curated_models(
    sqlite_database_path: Path,
    sqlite_database: SqliteDatabase,
) -> None:
    repository = build_repository(
        database_path=sqlite_database_path,
        database=sqlite_database,
    )

    models = await repository.get_many(
        workspace_id="workspace-1",
        resource_type="model",
        resource_ids=[
            "kimi-k2.6",
            "missing-model",
            "kimi-k2.6",
        ],
    )

    assert list(models) == [
        "kimi-k2.6",
    ]
    assert models["kimi-k2.6"].id == "kimi-k2.6"


@pytest.mark.asyncio
async def test_reference_lookup_isolated_by_workspace(
    sqlite_database_path: Path,
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    await create_workspace(
        workspace_id="workspace-2",
    )
    instruction_repository = SqliteInstructionRepository(
        sqlite_database_path,
    )

    await instruction_repository.create(
        build_instruction(
            instruction_id="persona-1",
            workspace_id="workspace-1",
        )
    )

    repository = build_repository(
        database_path=sqlite_database_path,
        database=sqlite_database,
    )

    resources = await repository.get_many(
        workspace_id="workspace-2",
        resource_type="persona",
        resource_ids=[
            "persona-1",
        ],
    )

    assert resources == {}
