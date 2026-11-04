"""Logical models currently available only through NVIDIA-hosted deployments."""

from datetime import date

from .helpers import TEXT
from ..types import (
    ModelCatalogEntry,
    ModelLab,
)


NVIDIA_MODEL_ITEMS: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        id="inkling",
        name="Inkling",
        vendor="Thinking Machines",
        lab=ModelLab.THINKING_MACHINES,
        family="Inkling",
        description=(
            "Efficient general-purpose reasoning model with adjustable "
            "latency and cost, recommended for coding agents, tool use and "
            "multimodal tasks."
        ),
        released_at=date(2026, 7, 15),
        capabilities=TEXT,
    ),
    ModelCatalogEntry(
        id="mistral-medium-3.5-128b",
        name="Mistral Medium 3.5 128B",
        vendor="Mistral AI",
        lab=ModelLab.MISTRAL,
        family="Mistral Medium",
        description=(
            "Frontier-class 128B multimodal model with configurable "
            "speed-quality trade-offs and premium cost, recommended for "
            "long-running coding agents and complex tool-driven work."
        ),
        released_at=date(2026, 4, 29),
        capabilities=TEXT,
    ),
    ModelCatalogEntry(
        id="deepseek-v4-flash",
        name="DeepSeek V4 Flash",
        vendor="DeepSeek",
        lab=ModelLab.DEEPSEEK,
        family="DeepSeek V4",
        description=(
            "Fast, low-cost reasoning model recommended for high-volume "
            "coding agents and general text workloads."
        ),
        released_at=date(2026, 4, 24),
        capabilities=TEXT,
    ),
)
