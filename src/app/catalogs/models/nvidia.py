"""Logical models currently available only through NVIDIA-hosted deployments."""

from ..providers import ProviderId
from .helpers import TEXT
from .types import (
    ModelCatalogEntry,
    ModelDeployment,
    ModelEndpoint,
)


NVIDIA_MODEL_CATALOG: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        id="inkling",
        name="Inkling",
        vendor="Thinking Machines",
        family="Inkling",
        description=(
            "Efficient general-purpose reasoning model with adjustable "
            "latency and cost, recommended for coding agents, tool use and "
            "multimodal tasks."
        ),
        capabilities=TEXT,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.NVIDIA,
                provider_model_id="thinkingmachines/inkling",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                max_output_tokens=8_192,
            ),
        ),
    ),
    ModelCatalogEntry(
        id="mistral-medium-3.5-128b",
        name="Mistral Medium 3.5 128B",
        vendor="Mistral AI",
        family="Mistral Medium",
        description=(
            "Frontier-class 128B multimodal model with configurable "
            "speed-quality trade-offs and premium cost, recommended for "
            "long-running coding agents and complex tool-driven work."
        ),
        capabilities=TEXT,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.NVIDIA,
                provider_model_id="mistralai/mistral-medium-3.5-128b",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                max_output_tokens=16_384,
            ),
        ),
    ),
    ModelCatalogEntry(
        id="deepseek-v4-flash",
        name="DeepSeek V4 Flash",
        vendor="DeepSeek",
        family="DeepSeek V4",
        description=(
            "Fast, low-cost reasoning model recommended for high-volume "
            "coding agents and general text workloads."
        ),
        capabilities=TEXT,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.NVIDIA,
                provider_model_id="deepseek-ai/deepseek-v4-flash",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                max_output_tokens=16_384,
            ),
        ),
    ),
)
