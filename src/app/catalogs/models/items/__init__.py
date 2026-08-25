"""Curated model items grouped by deployment provider."""

from .anthropic import ANTHROPIC_MODEL_ITEMS
from .nvidia import NVIDIA_MODEL_ITEMS
from .openai import OPENAI_MODEL_ITEMS
from .together import TOGETHER_MODEL_ITEMS


MODEL_ITEMS = (
    OPENAI_MODEL_ITEMS
    + ANTHROPIC_MODEL_ITEMS
    + TOGETHER_MODEL_ITEMS[-4:]
    + TOGETHER_MODEL_ITEMS[:-4]
    + NVIDIA_MODEL_ITEMS
)


__all__ = [
    "ANTHROPIC_MODEL_ITEMS",
    "MODEL_ITEMS",
    "NVIDIA_MODEL_ITEMS",
    "OPENAI_MODEL_ITEMS",
    "TOGETHER_MODEL_ITEMS",
]
