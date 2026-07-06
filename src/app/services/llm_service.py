"""
LLM provider service.

Centralises the external model invocations used by the harness.

The harness currently uses:

- Together.ai models to generate structured file operations;
- OpenAI models to review candidate changes using review skills.

Responsibilities include:

- lazily initialising provider SDK clients;
- validating provider API-key configuration;
- executing generator and reviewer model requests;
- applying provider-specific request parameters;
- parsing structured reviewer verdicts;
- normalising text, token usage and timing metrics across providers.

This service is the only application component that should depend directly
on LLM provider SDKs. It does not construct repository context, apply file
operations or orchestrate harness iterations.
"""

import asyncio
import json
import os
import time
from typing import Any

from dotenv import load_dotenv

from src.app.skills import load_skill


load_dotenv()


GENERATOR_SYSTEM_PROMPT = """
You are a senior software engineer.

Return ONLY valid JSON.

The JSON must have this exact shape:

{
  "operations": [
    {
      "operation": "create|replace|delete",
      "path": "relative/path/from/repo/root",
      "content": "full file content for create or replace"
    }
  ]
}

Rules:
- No Markdown fences.
- No prose before or after the JSON.
- Use relative paths only.
- Do not use absolute paths.
- Do not write outside the repository.
- Do not modify .git or .looping-louie.
- For create and replace, include the full final file content.
- For delete, omit content.
- Prefer small, focused changes.
""".strip()


REVIEWER_OUTPUT_INSTRUCTIONS = """
You must return valid JSON only.

The JSON object must have this exact shape:

{
  "approved": true,
  "feedback": "Review feedback"
}

Rules:
- approved must be a JSON boolean.
- feedback must be a JSON string.
- Do not include Markdown fences.
- Do not include prose before or after the JSON.
""".strip()


_openai_client = None
_together_client = None


def _get_openai_client():
    """
    Return the shared OpenAI client.

    The client and SDK are loaded lazily so importing this module does not
    require OpenAI configuration or initialise network resources.
    """
    global _openai_client

    if _openai_client is None:
        api_key = _require_api_key(
            variable_name="OPENAI_API_KEY",
            provider_name="OpenAI",
        )

        from openai import OpenAI

        _openai_client = OpenAI(
            api_key=api_key,
            timeout=60,
            max_retries=1,
        )

    return _openai_client


def _get_together_client():
    """
    Return the shared Together client.

    The client and SDK are loaded lazily so the application can start without
    Together configuration when that provider is not used.
    """
    global _together_client

    if _together_client is None:
        api_key = _require_api_key(
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
        max_tokens=12_000,
        temperature=0.2,
        reasoning={"enabled": False},
    )

    raw = _extract_response_text(
        response=response,
        provider_name="Together",
    )
    usage = getattr(response, "usage", None)

    return {
        "text": raw.strip(),
        **_normalise_usage(usage),
        "duration_ms": _elapsed_milliseconds(start),
    }


async def review_with_openai(
    model: str,
    original_prompt: str,
    candidate_output: str,
    skill: str,
) -> dict[str, Any]:
    """
    Execute one review skill using an OpenAI model.

    The selected skill becomes part of the system prompt. The user message
    contains the original task and the candidate diff together with the full
    changed-file contents.

    The synchronous provider SDK is executed in a worker thread so it does not
    block the application's asynchronous event loop.

    Args:
        model:
            OpenAI model identifier.

        original_prompt:
            Original user task being reviewed.

        candidate_output:
            Candidate Git diff and changed-file contents.

        skill:
            Name of the review skill to load.

    Returns:
        A provider-normalised dictionary containing:

        - approved;
        - feedback;
        - input_tokens;
        - output_tokens;
        - cached_input_tokens;
        - reasoning_tokens;
        - duration_ms.
    """
    start = time.perf_counter()
    client = _get_openai_client()
    skill_prompt = load_skill(skill)

    system_prompt = f"""
{skill_prompt}

{REVIEWER_OUTPUT_INSTRUCTIONS}
""".strip()

    user_prompt = f"""
Original user prompt:

{original_prompt}

Candidate diff and changed files:

{candidate_output}
""".strip()

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = _extract_response_text(
        response=response,
        provider_name="OpenAI",
    )
    verdict = _parse_reviewer_verdict(raw)
    usage = getattr(response, "usage", None)

    return {
        "approved": verdict["approved"],
        "feedback": verdict["feedback"],
        **_normalise_usage(usage),
        "duration_ms": _elapsed_milliseconds(start),
    }


def _parse_reviewer_verdict(raw: str) -> dict[str, Any]:
    """
    Parse and validate a structured reviewer response.

    Invalid or malformed reviewer responses are converted into explicit
    rejections so they can never approve a candidate accidentally.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "approved": False,
            "feedback": f"Reviewer returned invalid JSON: {raw}",
        }

    if not isinstance(data, dict):
        return {
            "approved": False,
            "feedback": (
                "Reviewer response must be a JSON object. "
                f"Received: {raw}"
            ),
        }

    approved = data.get("approved")

    if not isinstance(approved, bool):
        return {
            "approved": False,
            "feedback": (
                "Reviewer response must contain an 'approved' boolean. "
                f"Received: {raw}"
            ),
        }

    feedback = data.get("feedback")

    if feedback is None:
        feedback = data.get("summary")

    if not isinstance(feedback, str) or not feedback.strip():
        return {
            "approved": False,
            "feedback": (
                "Reviewer response must contain a non-empty 'feedback' "
                f"string. Received: {raw}"
            ),
        }

    return {
        "approved": approved,
        "feedback": feedback.strip(),
    }


def _extract_response_text(
    response: Any,
    provider_name: str,
) -> str:
    """
    Extract message text from an OpenAI-compatible chat completion response.

    Raises:
        RuntimeError:
            If the provider response does not contain usable message content.
    """
    choices = getattr(response, "choices", None)

    if not choices:
        raise RuntimeError(
            f"{provider_name} returned a response without choices"
        )

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)

    if message is None:
        raise RuntimeError(
            f"{provider_name} returned a choice without a message"
        )

    content = getattr(message, "content", None)

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            f"{provider_name} returned an empty response"
        )

    return content


def _normalise_usage(usage: Any) -> dict[str, int]:
    """
    Convert provider-specific token usage into the common metrics format.

    Missing or unsupported usage fields default to zero.
    """
    if usage is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
            "reasoning_tokens": 0,
        }

    input_tokens = _integer_attribute(
        usage,
        "prompt_tokens",
        fallback_attribute="input_tokens",
    )
    output_tokens = _integer_attribute(
        usage,
        "completion_tokens",
        fallback_attribute="output_tokens",
    )

    prompt_details = getattr(usage, "prompt_tokens_details", None)
    completion_details = getattr(
        usage,
        "completion_tokens_details",
        None,
    )

    cached_input_tokens = _integer_attribute(
        prompt_details,
        "cached_tokens",
    )
    reasoning_tokens = _integer_attribute(
        completion_details,
        "reasoning_tokens",
    )

    if cached_input_tokens == 0:
        cached_input_tokens = _integer_attribute(
            usage,
            "cached_input_tokens",
        )

    if reasoning_tokens == 0:
        reasoning_tokens = _integer_attribute(
            usage,
            "reasoning_tokens",
        )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached_input_tokens,
        "reasoning_tokens": reasoning_tokens,
    }


def _integer_attribute(
    value: Any,
    attribute: str,
    *,
    fallback_attribute: str | None = None,
) -> int:
    """
    Read a non-negative integer attribute from a provider response object.
    """
    if value is None:
        return 0

    result = getattr(value, attribute, None)

    if result is None and fallback_attribute is not None:
        result = getattr(value, fallback_attribute, None)

    if isinstance(result, bool):
        return 0

    if isinstance(result, int):
        return max(result, 0)

    return 0


def _require_api_key(
    variable_name: str,
    provider_name: str,
) -> str:
    """
    Return a configured provider API key.

    Raises:
        RuntimeError:
            If the required environment variable is missing or empty.
    """
    api_key = os.getenv(variable_name)

    if not api_key or not api_key.strip():
        raise RuntimeError(
            f"Missing {variable_name} required by {provider_name}"
        )

    return api_key.strip()


def _elapsed_milliseconds(start: float) -> int:
    """
    Return elapsed monotonic time in milliseconds.
    """
    return int((time.perf_counter() - start) * 1000)