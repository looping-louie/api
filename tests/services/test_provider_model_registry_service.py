"""Tests for the provider model registry."""

from src.app.catalogs.models import (
    ModelStatus,
    ProviderId,
)
from src.app.services.providers.model_registry_service import (
    CatalogModelRegistryService,
)
from tests.factories.models import (
    build_deployment,
    build_model,
)


def test_catalog_registry_counts_active_logical_models_once() -> None:
    catalog = (
        build_model(
            model_id="active-together",
            deployments=(
                build_deployment(
                    provider_id=ProviderId.TOGETHER,
                ),
                build_deployment(
                    provider_id=ProviderId.TOGETHER,
                    provider_model_id="vendor/second-deployment",
                ),
            ),
        ),
        build_model(
            model_id="active-openai",
            deployments=(
                build_deployment(
                    provider_id=ProviderId.OPENAI,
                ),
            ),
        ),
        build_model(
            model_id="deprecated-model",
            status=ModelStatus.DEPRECATED,
            deployments=(
                build_deployment(
                    provider_id=ProviderId.TOGETHER,
                ),
            ),
        ),
        build_model(
            model_id="deprecated-deployment",
            deployments=(
                build_deployment(
                    provider_id=ProviderId.TOGETHER,
                    status=ModelStatus.DEPRECATED,
                ),
            ),
        ),
    )

    registry = CatalogModelRegistryService(
        catalog=catalog,
    )

    assert registry.count_by_provider("together") == 1
    assert registry.count_by_provider("OPENAI") == 1
    assert registry.count_by_provider("anthropic") == 0
