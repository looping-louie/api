"""OpenAI curated model items."""

from datetime import date

from .helpers import GENERAL_REASONING, _pricing
from ..types import (
    ModelCatalogEntry,
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
        tags=("fast", "cost-efficient", "high-volume"),
    ),
)
