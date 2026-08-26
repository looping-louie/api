"""Contract tests for the curated logical model catalog."""

from typing import cast

import pytest

from src.app.catalogs.models import (
    CatalogIndex,
    MODEL_CATALOG,
    ModelCatalogEntry,
    ModelCatalogValidationError,
    ModelEndpoint,
    ModelLab,
    ProviderModelOffering,
    validate_model_catalog,
)
from src.app.catalogs.providers import ProviderCatalogEntry, ProviderId
from tests.factories.models import build_model


def build_provider(
    *offerings: ProviderModelOffering,
) -> ProviderCatalogEntry:
    """Build a provider definition that owns test model routes."""

    return ProviderCatalogEntry(
        id=ProviderId.TOGETHER,
        name='Together',
        description='Test provider',
        logo_url='/test.svg',
        requires_api_key=True,
        default_base_url='https://example.test',
        offerings=offerings,
    )


def build_offering(
    model_id: str = 'model-1',
    provider_model_id: str = 'vendor/model-1',
) -> ProviderModelOffering:
    """Build a provider-owned route for a logical model."""

    return ProviderModelOffering(
        model_id=model_id,
        provider_model_id=provider_model_id,
        endpoint=ModelEndpoint.CHAT_COMPLETIONS,
    )


def test_curated_model_catalog_is_valid() -> None:
    """The production catalog satisfies every identity and deployment rule."""

    validate_model_catalog(MODEL_CATALOG)


def test_rejects_duplicate_model_ids() -> None:
    """Catalog validation rejects duplicate logical model identifiers."""

    catalog = (
        build_model(model_id='duplicate-model'),
        build_model(model_id='duplicate-model'),
    )

    with pytest.raises(
        ModelCatalogValidationError,
        match="Duplicate model catalog id",
    ):
        validate_model_catalog(
            catalog,
            provider_catalog=(build_provider(build_offering('duplicate-model')),),
        )


def test_rejects_unknown_model_lab() -> None:
    """Catalog validation rejects labs outside the public typed taxonomy."""

    catalog = (
        build_model(
            lab=cast(ModelLab, "unknown-lab"),
        ),
    )

    with pytest.raises(
        ModelCatalogValidationError,
        match="unknown lab",
    ):
        validate_model_catalog(
            catalog,
            provider_catalog=(build_provider(build_offering()),),
        )


def test_rejects_duplicate_provider_deployments() -> None:
    """One provider model route cannot belong to two logical models."""

    catalog = (
        build_model(model_id='logical-model-one'),
        build_model(model_id='logical-model-two'),
    )

    with pytest.raises(
        ModelCatalogValidationError,
        match="Duplicate model deployment",
    ):
        validate_model_catalog(
            catalog,
            provider_catalog=(build_provider(
                build_offering('logical-model-one', 'vendor/shared-model'),
                build_offering('logical-model-two', 'vendor/shared-model'),
            ),),
        )


def test_rejects_offering_for_unknown_model() -> None:
    """Provider offerings must reference a declared logical model."""

    catalog = (
        build_model(),
    )

    with pytest.raises(
        ModelCatalogValidationError,
        match='unknown model',
    ):
        validate_model_catalog(
            catalog,
            provider_catalog=(build_provider(build_offering('missing-model')),),
        )


def test_provider_offerings_derive_model_deployments() -> None:
    """The index exposes provider-owned routes as runtime deployments."""

    catalog: tuple[ModelCatalogEntry, ...] = (
        build_model(model_id='multi-provider-model'),
    )

    provider = build_provider(
        build_offering('multi-provider-model', 'vendor/together-route'),
    )
    validate_model_catalog(catalog, provider_catalog=(provider,))

    deployments = CatalogIndex(
        models=catalog,
        providers=(provider,),
    ).deployments_for_model('multi-provider-model')

    assert deployments[0].provider_id == ProviderId.TOGETHER
    assert deployments[0].provider_model_id == 'vendor/together-route'
