"""Factories for deterministic curated-model test data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.app.catalogs.models import (
    ModelCapability,
    ModelCatalogEntry,
    ModelDeployment,
    ModelEndpoint,
    ModelLab,
    ModelPricing,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId


def build_deployment(
    *,
    provider_id: ProviderId = ProviderId.TOGETHER,
    provider_model_id: str = "vendor/model-1",
    status: ModelStatus = ModelStatus.ACTIVE,
    input_price: str = "1.00",
    output_price: str = "2.00",
) -> ModelDeployment:
    """Build a model deployment for tests."""

    return ModelDeployment(
        provider_id=provider_id,
        provider_model_id=provider_model_id,
        endpoint=ModelEndpoint.CHAT_COMPLETIONS,
        context_window=128_000,
        max_output_tokens=16_000,
        pricing=ModelPricing(
            input_per_million_usd=Decimal(input_price),
            output_per_million_usd=Decimal(output_price),
        ),
        status=status,
    )


def build_model(
    *,
    model_id: str = "model-1",
    name: str = "Model One",
    vendor: str = "Vendor",
    lab: ModelLab = ModelLab.OPENAI,
    family: str = "Family",
    description: str = "Test model",
    released_at: date = date(2026, 1, 1),
    status: ModelStatus = ModelStatus.ACTIVE,
    capabilities: frozenset[ModelCapability] | None = None,
    deployments: tuple[ModelDeployment, ...] | None = None,
    replacement_model_id: str | None = None,
    tags: tuple[str, ...] = ("test",),
) -> ModelCatalogEntry:
    """Build a catalog model for tests."""

    return ModelCatalogEntry(
        id=model_id,
        name=name,
        vendor=vendor,
        lab=lab,
        family=family,
        description=description,
        released_at=released_at,
        capabilities=capabilities
        or frozenset(
            {
                ModelCapability.TEXT,
            }
        ),
        deployments=deployments
        or (
            build_deployment(),
        ),
        status=status,
        replacement_model_id=replacement_model_id,
        tags=tags,
    )
