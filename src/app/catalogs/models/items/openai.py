"""OpenAI curated model items."""

from datetime import date

from ...providers import ProviderId
from .helpers import GENERAL_REASONING, _pricing
from ..types import (
    ModelCatalogEntry,
    ModelDeployment,
    ModelEndpoint,
    ModelLab,
)


OPENAI_MODEL_ITEMS: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        id="gpt-5.6-sol",
        name="GPT-5.6 Sol",
        vendor="OpenAI",
        lab=ModelLab.OPENAI,
        family="GPT-5.6",
        description="OpenAI flagship for complex reasoning and coding.",
        released_at=date(2026, 7, 9),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.OPENAI,
                provider_model_id="gpt-5.6-sol",
                endpoint=ModelEndpoint.RESPONSES,
                context_window=1_050_000,
                max_output_tokens=128_000,
                pricing=_pricing("5.00", "30.00", "0.50"),
            ),
        ),
        tags=("frontier", "coding", "reasoning"),
    ),
    ModelCatalogEntry(
        id="gpt-5.6-terra",
        name="GPT-5.6 Terra",
        vendor="OpenAI",
        lab=ModelLab.OPENAI,
        family="GPT-5.6",
        description="Balanced OpenAI model for quality, latency and cost.",
        released_at=date(2026, 7, 9),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.OPENAI,
                provider_model_id="gpt-5.6-terra",
                endpoint=ModelEndpoint.RESPONSES,
                context_window=1_050_000,
                max_output_tokens=128_000,
                pricing=_pricing("2.50", "15.00", "0.25"),
            ),
        ),
        tags=("balanced", "coding", "reasoning"),
    ),
    ModelCatalogEntry(
        id="gpt-5.6-luna",
        name="GPT-5.6 Luna",
        vendor="OpenAI",
        lab=ModelLab.OPENAI,
        family="GPT-5.6",
        description="Cost-efficient OpenAI model for high-volume workloads.",
        released_at=date(2026, 7, 9),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.OPENAI,
                provider_model_id="gpt-5.6-luna",
                endpoint=ModelEndpoint.RESPONSES,
                context_window=1_050_000,
                max_output_tokens=128_000,
                pricing=_pricing("1.00", "6.00", "0.10"),
            ),
        ),
        tags=("fast", "cost-efficient", "high-volume"),
    ),
)
