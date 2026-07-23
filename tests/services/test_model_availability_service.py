import pytest

from src.app.catalogs.models import ModelStatus
from src.app.catalogs.providers import ProviderId
from src.app.services.model_service import (
    ModelAvailabilityService,
    ModelUnavailableReason,
    ProviderConnectionState,
)
from tests.factories.models import (
    build_deployment,
    build_model,
)
from tests.fakes.provider_state_repository import (
    FakeProviderStateRepository,
)


@pytest.mark.asyncio
async def test_model_is_available_when_provider_is_enabled(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    service = ModelAvailabilityService(
        provider_state_repository=provider_state_repository,
    )

    availability = await service.describe(
        workspace_id="workspace-1",
        model=build_model(),
    )

    assert availability.available is True
    assert availability.providers[0].available is True
    assert availability.providers[0].reason is None


@pytest.mark.asyncio
async def test_model_is_unavailable_when_provider_is_not_configured(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    service = ModelAvailabilityService(
        provider_state_repository=provider_state_repository,
    )

    availability = await service.describe(
        workspace_id="workspace-1",
        model=build_model(),
    )

    provider = availability.providers[0]

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
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=False,
        ),
    )
    service = ModelAvailabilityService(
        provider_state_repository=provider_state_repository,
    )

    availability = await service.describe(
        workspace_id="workspace-1",
        model=build_model(),
    )

    provider = availability.providers[0]

    assert availability.available is False
    assert provider.configured is True
    assert provider.enabled is False
    assert provider.reason == ModelUnavailableReason.PROVIDER_DISABLED


@pytest.mark.asyncio
async def test_deprecated_model_is_never_available(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    service = ModelAvailabilityService(
        provider_state_repository=provider_state_repository,
    )

    availability = await service.describe(
        workspace_id="workspace-1",
        model=build_model(
            status=ModelStatus.DEPRECATED,
        ),
    )

    assert availability.available is False
    assert availability.providers[0].reason == (
        ModelUnavailableReason.MODEL_DEPRECATED
    )


@pytest.mark.asyncio
async def test_deprecated_deployment_is_not_available(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    service = ModelAvailabilityService(
        provider_state_repository=provider_state_repository,
    )
    model = build_model(
        deployments=(
            build_deployment(
                status=ModelStatus.DEPRECATED,
            ),
        ),
    )

    availability = await service.describe(
        workspace_id="workspace-1",
        model=model,
    )

    assert availability.available is False
    assert availability.providers[0].reason == (
        ModelUnavailableReason.DEPLOYMENT_DEPRECATED
    )


@pytest.mark.asyncio
async def test_describe_many_loads_provider_states_once(
    provider_state_repository: FakeProviderStateRepository,
) -> None:
    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.TOGETHER,
            configured=True,
            enabled=True,
        ),
    )
    provider_state_repository.seed(
        workspace_id="workspace-1",
        state=ProviderConnectionState(
            provider_id=ProviderId.OPENAI,
            configured=True,
            enabled=False,
        ),
    )
    service = ModelAvailabilityService(
        provider_state_repository=provider_state_repository,
    )
    models = (
        build_model(
            model_id="together-model",
        ),
        build_model(
            model_id="openai-model",
            deployments=(
                build_deployment(
                    provider_id=ProviderId.OPENAI,
                    provider_model_id="openai/model",
                ),
            ),
        ),
    )

    availability = await service.describe_many(
        workspace_id="workspace-1",
        models=models,
    )

    assert availability["together-model"].available is True
    assert availability["openai-model"].available is False
    assert len(provider_state_repository.calls) == 1
    assert provider_state_repository.calls[0] == (
        "workspace-1",
        (
            ProviderId.TOGETHER,
            ProviderId.OPENAI,
        ),
    )
