"""Anthropic curated model items."""

from datetime import date

from .helpers import GENERAL_REASONING, _pricing
from ..types import (
    ModelCatalogEntry,
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
        tags=("fast", "cost-efficient", "high-volume"),
    ),
)
