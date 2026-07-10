"""Metric helpers for harness execution."""


def tokens_per_second(
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
) -> float:
    """Compute throughput for a model call."""
    total_tokens = input_tokens + output_tokens
    return round(
        total_tokens / max(duration_ms / 1000, 0.001),
        2,
    )
