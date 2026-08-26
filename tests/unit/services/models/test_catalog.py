"""Tests for filtering and describing the curated model catalog."""

from datetime import date

import pytest

from src.app.catalogs.models import (
    CatalogIndex,
    ModelCapability,
    ModelLab,
    ModelSort,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId
from src.app.services.models.availability import (
    ModelAvailabilityService,
    ModelNotFoundError,
    ProviderConnectionState,
)
from src.app.services.models.catalog import ModelCatalogService
from src.app.services.shared.tenant import TenantService
from tests.factories.models import (
    build_model,
    build_offering,
    build_provider,
)
from tests.fakes.provider_state_repository import (
    FakeProviderStateRepository,
)


def build_service(
    *,
    tenant_service: TenantService,
    repository: FakeProviderStateRepository,
) -> ModelCatalogService:
    """Build a catalog service with models that distinguish every filter."""

    catalog = (
        build_model(
            model_id="coding-model",
            name="Coding Model",
            vendor="Vendor A",
            lab=ModelLab.DEEPSEEK,
            released_at=date(2026, 2, 1),
            capabilities=frozenset(
                {
                    ModelCapability.TEXT,
                    ModelCapability.CODING,
                }
            ),
            tags=("coding", "fast"),
        ),
        build_model(
            model_id="openai-model",
            name="OpenAI Model",
            vendor="OpenAI",
            lab=ModelLab.OPENAI,
            released_at=date(2026, 3, 1),
            tags=("reasoning",),
        ),
        build_model(
            model_id="deprecated-model",
            name="Deprecated Model",
            vendor="Vendor A",
            lab=ModelLab.META,
            released_at=date(2026, 1, 1),
            status=ModelStatus.DEPRECATED,
        ),
    )
    catalog_index = CatalogIndex(
        models=catalog,
        providers=(
            build_provider(
                build_offering(model_id="coding-model"),
                build_offering(model_id="deprecated-model"),
            ),
            build_provider(
                build_offering(
                    model_id="openai-model",
                    provider_model_id="openai/model",
                ),
                provider_id=ProviderId.OPENAI,
            ),
        ),
    )

    return ModelCatalogService(
        tenant_service=tenant_service,
        availability_service=ModelAvailabilityService(
                linked_service_repository=repository,
        ),
        catalog=catalog,
        catalog_index=catalog_index,
    )


@pytest.mark.asyncio
async def test_list_excludes_deprecated_models_by_default(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Deprecated models stay hidden when no lifecycle filter is supplied."""

    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    models = await service.list(
        user_id="user-1",
        workspace_id="workspace-1",
    )

    assert [
        model.id
        for model in models
    ] == [
        "coding-model",
        "openai-model",
    ]


@pytest.mark.asyncio
async def test_list_can_include_deprecated_models(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """The opt-in flag returns deprecated models alongside current models."""

    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    models = await service.list(
        user_id="user-1",
        workspace_id="workspace-1",
        include_deprecated=True,
    )

    assert {
        model.id
        for model in models
    } == {
        "coding-model",
        "openai-model",
        "deprecated-model",
    }


@pytest.mark.asyncio
async def test_list_can_select_deprecated_status_directly(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """An explicit deprecated status overrides default catalog exclusion."""

    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    models = await service.list(
        user_id="user-1",
        workspace_id="workspace-1",
        model_status=ModelStatus.DEPRECATED,
    )

    assert [model.id for model in models] == ["deprecated-model"]


@pytest.mark.asyncio
async def test_list_filters_by_multiple_labs(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Repeated lab filters use OR semantics across typed lab values."""

    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    models = await service.list(
        user_id="user-1",
        workspace_id="workspace-1",
        labs=(ModelLab.OPENAI, ModelLab.DEEPSEEK),
        include_deprecated=True,
    )

    assert [model.id for model in models] == [
        "coding-model",
        "openai-model",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sort", "expected_ids"),
    [
        (
            ModelSort.ALPHABETICAL_ASC,
            ["coding-model", "deprecated-model", "openai-model"],
        ),
        (
            ModelSort.ALPHABETICAL_DESC,
            ["openai-model", "deprecated-model", "coding-model"],
        ),
        (
            ModelSort.NEWEST,
            ["openai-model", "coding-model", "deprecated-model"],
        ),
        (
            ModelSort.OLDEST,
            ["deprecated-model", "coding-model", "openai-model"],
        ),
    ],
)
async def test_list_sorts_models(
    sort: ModelSort,
    expected_ids: list[str],
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Every public sort produces the expected catalog order."""

    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    models = await service.list(
        user_id="user-1",
        workspace_id="workspace-1",
        include_deprecated=True,
        sort=sort,
    )

    assert [model.id for model in models] == expected_ids


@pytest.mark.asyncio
async def test_list_filters_by_provider_capability_and_search(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Provider, capability, and search filters compose with AND semantics."""

    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    models = await service.list(
        user_id="user-1",
        workspace_id="workspace-1",
        provider_id=ProviderId.TOGETHER,
        capability=ModelCapability.CODING,
        search="fast",
    )

    assert [
        model.id
        for model in models
    ] == [
        "coding-model",
    ]


@pytest.mark.asyncio
async def test_list_filters_by_workspace_availability(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Availability filtering uses the selected workspace provider state."""

    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.OPENAI,
            configured=True,
            enabled=True,
        ),
    )
    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    models = await service.list(
        user_id="user-1",
        workspace_id="workspace-1",
        available=True,
    )

    assert [
        model.id
        for model in models
    ] == [
        "openai-model",
    ]


@pytest.mark.asyncio
async def test_describe_returns_complete_model(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Describe returns catalog details enriched with availability."""

    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    model = await service.describe(
        user_id="user-1",
        workspace_id="workspace-1",
        model_id="coding-model",
    )

    assert model.id == "coding-model"
    assert model.available is True
    assert model.offerings[0].provider_id == ProviderId.TOGETHER


@pytest.mark.asyncio
async def test_describe_rejects_unknown_model(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Describe rejects identifiers absent from the curated catalog."""

    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    with pytest.raises(ModelNotFoundError):
        await service.describe(
            user_id="user-1",
            workspace_id="workspace-1",
            model_id="missing-model",
        )


def test_get_many_omits_unknown_models(
    tenant_service: TenantService,
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    """Bulk lookup preserves known IDs and omits unknown references."""

    service = build_service(
        tenant_service=tenant_service,
        repository=provider_state_repository,
    )

    models = service.get_many(
        model_ids=[
            "coding-model",
            "missing-model",
            "openai-model",
        ],
    )

    assert list(models) == [
        "coding-model",
        "openai-model",
    ]
