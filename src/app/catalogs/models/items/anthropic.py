"""Anthropic curated model items."""

from datetime import date

from ...providers import ProviderId
from .helpers import GENERAL_REASONING, _pricing
from ..types import (
    ModelCatalogEntry,
    ModelDeployment,
    ModelEndpoint,
    ModelLab,
)


ANTHROPIC_MODEL_ITEMS: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        id="claude-fable-5",
        name="Claude Fable 5",
        vendor="Anthropic",
        lab=ModelLab.ANTHROPIC,
        family="Claude 5",
        description="Anthropic model for long-running and demanding agents.",
        released_at=date(2026, 6, 9),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.ANTHROPIC,
                provider_model_id="claude-fable-5",
                endpoint=ModelEndpoint.MESSAGES,
                context_window=1_000_000,
                max_output_tokens=128_000,
                pricing=_pricing("10.00", "50.00"),
            ),
        ),
        tags=("frontier", "agents", "reasoning"),
    ),
    ModelCatalogEntry(
        id="claude-opus-4.8",
        name="Claude Opus 4.8",
        vendor="Anthropic",
        lab=ModelLab.ANTHROPIC,
        family="Claude 4",
        description="Anthropic model for agentic coding and enterprise work.",
        released_at=date(2026, 5, 28),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.ANTHROPIC,
                provider_model_id="claude-opus-4-8",
                endpoint=ModelEndpoint.MESSAGES,
                context_window=1_000_000,
                max_output_tokens=128_000,
                pricing=_pricing("5.00", "25.00"),
            ),
        ),
        tags=("coding", "agents", "enterprise"),
    ),
    ModelCatalogEntry(
        id="claude-sonnet-5",
        name="Claude Sonnet 5",
        vendor="Anthropic",
        lab=ModelLab.ANTHROPIC,
        family="Claude 5",
        description="Anthropic model balancing speed and intelligence.",
        released_at=date(2026, 6, 30),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.ANTHROPIC,
                provider_model_id="claude-sonnet-5",
                endpoint=ModelEndpoint.MESSAGES,
                context_window=1_000_000,
                max_output_tokens=128_000,
                pricing=_pricing(
                    "2.00",
                    "10.00",
                    valid_until=date(2026, 8, 31),
                    note="Introductory pricing.",
                ),
            ),
        ),
        tags=("balanced", "coding", "agents"),
    ),
    ModelCatalogEntry(
        id="claude-haiku-4.5",
        name="Claude Haiku 4.5",
        vendor="Anthropic",
        lab=ModelLab.ANTHROPIC,
        family="Claude 4",
        description="Fast Anthropic model for cost-sensitive workloads.",
        released_at=date(2025, 10, 15),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.ANTHROPIC,
                provider_model_id="claude-haiku-4-5-20251001",
                endpoint=ModelEndpoint.MESSAGES,
                context_window=200_000,
                max_output_tokens=64_000,
                pricing=_pricing("1.00", "5.00"),
            ),
        ),
        tags=("fast", "cost-efficient", "high-volume"),
    ),
)
