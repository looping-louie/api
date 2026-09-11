"""Factories for deterministic curated-model test data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.app.catalogs.models import (
    CatalogIndex,
    ModelCapability,
    ModelCatalogEntry,
    ModelEndpoint,
    ModelLab,
    ModelPricing,
    ModelStatus,
    ProviderModelOffering,
)
from src.app.catalogs.providers import ProviderCatalogEntry, ProviderId


def build_offering(
    *,
    model_id: str = "model-1",
    provider_model_id: str = "vendor/model-1",
    endpoint: ModelEndpoint = ModelEndpoint.CHAT_COMPLETIONS,
    context_window: int | None = None,
    max_output_tokens: int | None = None,
    status: ModelStatus = ModelStatus.ACTIVE,
    input_price: str = "1.00",
    output_price: str = "2.00",
) -> ProviderModelOffering:
    """Build a provider-owned model offering for tests."""

    return ProviderModelOffering(
        model_id=model_id,
        provider_model_id=provider_model_id,
        endpoint=endpoint,
        context_window=context_window,
        max_output_tokens=max_output_tokens,
        pricing=ModelPricing(
            input_per_million_usd=Decimal(input_price),
            output_per_million_usd=Decimal(output_price),
        ),
        status=status,
    )


def build_provider(
    *offerings: ProviderModelOffering,
    provider_id: ProviderId = ProviderId.TOGETHER,
) -> ProviderCatalogEntry:
    """Build a provider entry that owns the supplied offerings."""

    return ProviderCatalogEntry(
        id=provider_id,
        name=provider_id.value.title(),
        description="Test provider",
        logo_url="/test.svg",
        requires_api_key=True,
        default_base_url="https://example.test",
        offerings=offerings,
    )


def build_catalog_index(
    *,
    models: tuple[ModelCatalogEntry, ...],
    providers: tuple[ProviderCatalogEntry, ...],
) -> CatalogIndex:
    """Build an index that derives offerings from test provider entries."""

    return CatalogIndex(
        models=models,
        providers=providers,
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
        status=status,
        replacement_model_id=replacement_model_id,
        tags=tags,
    )
