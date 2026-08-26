import pytest

from src.app.catalogs.models import (
    CatalogIndex,
    ModelCatalogEntry,
    ModelOffering,
    ModelStatus,
    ProviderModelOffering,
)
from src.app.catalogs.providers import ProviderId
from src.app.services.models.availability import (
    ModelAvailabilityService,
    ModelUnavailableReason,
    ProviderConnectionState,
)
from tests.factories.models import (
    build_offering,
    build_model,
    build_provider,
)
from tests.fakes.provider_state_repository import (
    FakeProviderStateRepository,
)


def offerings_for_model(
    model: ModelCatalogEntry,
    *offerings: ProviderModelOffering,
) -> tuple[ModelOffering, ...]:
    """Derive runtime offerings from test provider-owned declarations."""

    return CatalogIndex(
        models=(model,),
        providers=(build_provider(
            *(offerings or (build_offering(model_id=model.id),)),
        ),),
    ).offerings_for_model(model.id)


@pytest.mark.asyncio
async def test_model_is_available_when_provider_is_enabled(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        user_id="user-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    service = ModelAvailabilityService(
        linked_service_repository=provider_state_repository,
    )

    model = build_model()
    availability = await service.describe(
        user_id="user-1",
        model=model,
        offerings=offerings_for_model(model),
    )

    assert availability.available is True
    assert availability.offerings[0].available is True
    assert availability.offerings[0].reason is None


@pytest.mark.asyncio
async def test_model_is_unavailable_when_provider_is_not_configured(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    service = ModelAvailabilityService(
        linked_service_repository=provider_state_repository,
    )

    model = build_model()
    availability = await service.describe(
        user_id="user-1",
        model=model,
        offerings=offerings_for_model(model),
    )

    provider = availability.offerings[0]

    assert availability.available is False
    assert provider.configured is False
    assert provider.enabled is False
    assert provider.reason == (
        ModelUnavailableReason.PROVIDER_NOT_CONFIGURED
    )


@pytest.mark.asyncio
async def test_model_is_unavailable_when_provider_is_disabled(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        user_id="user-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=False,
        ),
    )
    service = ModelAvailabilityService(
        linked_service_repository=provider_state_repository,
    )

    model = build_model()
    availability = await service.describe(
        user_id="user-1",
        model=model,
        offerings=offerings_for_model(model),
    )

    provider = availability.offerings[0]

    assert availability.available is False
    assert provider.configured is True
    assert provider.enabled is False
    assert provider.reason == ModelUnavailableReason.PROVIDER_DISABLED


@pytest.mark.asyncio
async def test_deprecated_model_is_never_available(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        user_id="user-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    service = ModelAvailabilityService(
        linked_service_repository=provider_state_repository,
    )

    model = build_model(
        status=ModelStatus.DEPRECATED,
    )
    availability = await service.describe(
        user_id="user-1",
        model=model,
        offerings=offerings_for_model(model),
    )

    assert availability.available is False
    assert availability.offerings[0].reason == (
        ModelUnavailableReason.MODEL_DEPRECATED
    )


@pytest.mark.asyncio
async def test_deprecated_offering_is_not_available(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        user_id="user-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    service = ModelAvailabilityService(
        linked_service_repository=provider_state_repository,
    )
    model = build_model(
    )

    availability = await service.describe(
        user_id="user-1",
        model=model,
        offerings=offerings_for_model(
            model,
            build_offering(status=ModelStatus.DEPRECATED),
        ),
    )

    assert availability.available is False
    assert availability.offerings[0].reason == (
        ModelUnavailableReason.DEPLOYMENT_DEPRECATED
    )


@pytest.mark.asyncio
async def test_describe_many_loads_provider_states_once(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        user_id="user-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    provider_state_repository.seed(
        user_id="user-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.OPENAI,
            configured=True,
            enabled=False,
        ),
    )
    service = ModelAvailabilityService(
        linked_service_repository=provider_state_repository,
    )
    models = (
        build_model(model_id="together-model"),
        build_model(model_id="openai-model"),
    )
    catalog_index = CatalogIndex(
        models=models,
        providers=(
            build_provider(build_offering(model_id="together-model")),
            build_provider(
                build_offering(
                    model_id="openai-model",
                    provider_model_id="openai/model",
                ),
                provider_id=ProviderId.OPENAI,
            ),
        ),
    )

    availability = await service.describe_many(
        user_id="user-1",
        models=models,
        offerings_by_model={
            model.id: catalog_index.offerings_for_model(model.id)
            for model in models
        },
    )

    assert availability["together-model"].available is True
    assert availability["openai-model"].available is False
    assert len(provider_state_repository.calls) == 1
    assert provider_state_repository.calls == ['user-1']
