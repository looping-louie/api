import asyncio
import time
from typing import Any
from .utils import (
    require_api_key,
    extract_response_text,
    normalise_usage,
    elapsed_milliseconds,
)
from .instructions import GENERATOR_SYSTEM_PROMPT


_together_client = None

MAX_OUTPUT_TOKENS = 12_000

TRUNCATED_FINISH_REASONS = {
    "length",
    "max_tokens",
}

def _extract_finish_reason(response: Any) -> str | None:
    """
    Extract the completion finish reason from a Together response.

    Supports both SDK model objects and dictionary-shaped responses.
    """
    choices = getattr(response, "choices", None)

    if not choices:
        return None

    first_choice = choices[0]

    if isinstance(first_choice, dict):
        finish_reason = first_choice.get("finish_reason")
    else:
        finish_reason = getattr(first_choice, "finish_reason", None)

    if isinstance(finish_reason, str):
        return finish_reason

    return None


def _get_together_client():
    """
    Return the shared Together client.

    The client and SDK are loaded lazily so the application can start without
    Together configuration when that provider is not used.
    """
    global _together_client

    if _together_client is None:
        api_key = require_api_key(
            variable_name="TOGETHER_API_KEY",
            provider_name="Together",
        )

        from together import Together

        _together_client = Together(api_key=api_key)

    return _together_client


async def call_together(
    model: str,
    prompt: str,
) -> dict[str, Any]:
    """
    Execute a generator model through Together.ai.

    The generator receives a system-level file-operation contract and the
    prompt constructed by ModelContextService.

    The synchronous provider SDK is executed in a worker thread so it does not
    block the application's asynchronous event loop.

    Args:
        model:
            Together model identifier.

        prompt:
            Complete generator prompt.

    Returns:
        A provider-normalised dictionary containing:

        - text;
        - input_tokens;
        - output_tokens;
        - cached_input_tokens;
        - reasoning_tokens;
        - duration_ms.
    """
    start = time.perf_counter()
    client = _get_together_client()

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[
            {
                "role": "system",
                "content": GENERATOR_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        stream=False,
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=0.2,
        reasoning={"enabled": False},
    )

    raw = extract_response_text(
        response=response,
        provider_name="Together",
    )
    usage = getattr(response, "usage", None)
    usage_data = normalise_usage(usage)
    finish_reason = _extract_finish_reason(response)

    reached_output_limit = (
        finish_reason in TRUNCATED_FINISH_REASONS
        or (
            finish_reason is None
            and usage_data.get("output_tokens", 0)
            >= MAX_OUTPUT_TOKENS
        )
    )

    return {
        "text": raw.strip(),
        **usage_data,
        "finish_reason": finish_reason,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "reached_output_limit": reached_output_limit,
        "duration_ms": elapsed_milliseconds(start),
    }