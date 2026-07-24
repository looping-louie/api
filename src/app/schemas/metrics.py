"""Metrics-related schemas."""

from pydantic import BaseModel


class ModelMetrics(BaseModel):
    """
    Performance metrics collected from one LLM invocation.

    These metrics are provider-agnostic so they can represent Together,
    OpenAI, Anthropic or future providers uniformly.
    """

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    duration_ms: int = 0
    tokens_per_second: float = 0


__all__ = ['ModelMetrics']
