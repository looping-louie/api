"""Contract tests for the curated logical model catalog."""

from typing import cast

import pytest

from src.app.catalogs.models import (
    MODEL_CATALOG,
    ModelCatalogEntry,
    ModelCatalogValidationError,
    ModelLab,
    validate_model_catalog,
)
from src.app.catalogs.providers import ProviderId
from tests.factories.models import (
    build_deployment,
    build_model,
)


def test_curated_model_catalog_is_valid() -> None:
    """The production catalog satisfies every identity and deployment rule."""

    validate_model_catalog(MODEL_CATALOG)


def test_rejects_duplicate_model_ids() -> None:
    """Catalog validation rejects duplicate logical model identifiers."""

    catalog = (
        build_model(
            model_id="duplicate-model",
            deployments=(
                build_deployment(
                    provider_model_id="vendor/model-one",
                ),
            ),
        ),
        build_model(
            model_id="duplicate-model",
            deployments=(
                build_deployment(
                    provider_model_id="vendor/model-two",
                ),
            ),
        ),
    )

    with pytest.raises(
        ModelCatalogValidationError,
        match="Duplicate model catalog id",
    ):
        validate_model_catalog(catalog)


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
        validate_model_catalog(catalog)


def test_rejects_duplicate_provider_deployments() -> None:
    """One provider model route cannot belong to two logical models."""

    catalog = (
        build_model(
            model_id="logical-model-one",
            deployments=(
                build_deployment(
                    provider_id=ProviderId.TOGETHER,
                    provider_model_id="vendor/shared-model",
                ),
            ),
        ),
        build_model(
            model_id="logical-model-two",
            deployments=(
                build_deployment(
                    provider_id=ProviderId.TOGETHER,
                    provider_model_id="vendor/shared-model",
                ),
            ),
        ),
    )

    with pytest.raises(
        ModelCatalogValidationError,
        match="Duplicate model deployment",
    ):
        validate_model_catalog(catalog)


def test_rejects_deployment_for_unknown_provider() -> None:
    """Every deployment must reference a provider from the curated catalog."""

    catalog = (
        build_model(
            deployments=(
                build_deployment(
                    provider_id=cast(
                        ProviderId,
                        "unknown-provider",
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(
        ModelCatalogValidationError,
        match="unknown provider",
    ):
        validate_model_catalog(catalog)


def test_one_logical_model_can_have_multiple_provider_deployments() -> None:
    """A logical model may expose independent routes through several providers."""

    catalog: tuple[ModelCatalogEntry, ...] = (
        build_model(
            model_id="multi-provider-model",
            deployments=(
                build_deployment(
                    provider_id=ProviderId.OPENAI,
                    provider_model_id="vendor/openai-route",
                ),
                build_deployment(
                    provider_id=ProviderId.TOGETHER,
                    provider_model_id="vendor/together-route",
                ),
            ),
        ),
    )

    validate_model_catalog(catalog)
