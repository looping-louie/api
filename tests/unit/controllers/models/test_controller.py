import pytest

from src.app.catalogs.models import ModelCapability
from src.app.catalogs.providers import ProviderId
from src.app.controllers.model import ModelController
from src.app.services.models.availability import ProviderConnectionState
from tests.fakes.provider_state_repository import (
    FakeProviderStateRepository,
)


@pytest.mark.asyncio
async def test_controller_lists_models(
    model_controller: ModelController,
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

    response = await model_controller.list(
        user_id="user-1",
        workspace_id="workspace-1",
        provider_id=ProviderId.TOGETHER,
        capability=ModelCapability.TEXT,
        available=True,
    )

    assert response.total > 0
    assert all(
        model.available
        for model in response.items
    )
    assert all(
        any(
            offering.provider_id == ProviderId.TOGETHER
            for offering in model.offerings
        )
        for model in response.items
    )


@pytest.mark.asyncio
async def test_controller_describes_model(
    model_controller: ModelController,
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

    response = await model_controller.describe(
        user_id="user-1",
        workspace_id="workspace-1",
        model_id="kimi-k2.6",
    )

    assert response.id == "kimi-k2.6"
    assert response.available is True
    assert response.offerings[0].provider_id == ProviderId.TOGETHER
