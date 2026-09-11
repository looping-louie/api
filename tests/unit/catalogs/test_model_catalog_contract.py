"""Contract tests for the curated logical model catalog."""

from typing import cast

import pytest

from src.app.catalogs.models import (
    CatalogIndex,
    MODEL_CATALOG,
    ModelCatalogEntry,
    ModelCatalogValidationError,
    ModelLab,
    validate_model_catalog,
)
from src.app.catalogs.providers import ProviderId
from tests.factories.models import build_model, build_offering, build_provider


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
            provider_catalog=(build_provider(
                build_offering(model_id='duplicate-model'),
            ),),
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


def test_rejects_duplicate_provider_offerings() -> None:
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
                build_offering(
                    model_id='logical-model-one',
                    provider_model_id='vendor/shared-model',
                ),
                build_offering(
                    model_id='logical-model-two',
                    provider_model_id='vendor/shared-model',
                ),
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
            provider_catalog=(build_provider(
                build_offering(model_id='missing-model'),
            ),),
        )


def test_provider_offerings_derive_model_offerings() -> None:
    """The index exposes provider-owned routes as runtime offerings."""

    catalog: tuple[ModelCatalogEntry, ...] = (
        build_model(model_id='multi-provider-model'),
    )

    provider = build_provider(
        build_offering(
            model_id='multi-provider-model',
            provider_model_id='vendor/together-route',
        ),
    )
    validate_model_catalog(catalog, provider_catalog=(provider,))

    offerings = CatalogIndex(
        models=catalog,
        providers=(provider,),
    ).offerings_for_model('multi-provider-model')

    assert offerings[0].provider_id == ProviderId.TOGETHER
    assert offerings[0].provider_model_id == 'vendor/together-route'
