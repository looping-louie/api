import json
import os
import time
from typing import Any
from dotenv import load_dotenv


load_dotenv()


def _invalid_reviewer_verdict(message: str) -> dict[str, Any]:
    return {
        "score": 0,
        "blocking_issues": [
            {
                "title": "Invalid reviewer response",
                "description": message,
                "file": None,
            }
        ],
        "feedback": message,
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


def require_api_key(
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


def parse_reviewer_verdict(raw: str) -> dict[str, Any]:
    """
    Parse reviewer output fail-closed.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _invalid_reviewer_verdict(
            f"Reviewer returned invalid JSON: {raw}"
        )

    if not isinstance(data, dict):
        return _invalid_reviewer_verdict(
            "Reviewer response must be a JSON object"
        )

    score = data.get("score")

    if (
        isinstance(score, bool)
        or not isinstance(score, int)
        or not 0 <= score <= 100
    ):
        return _invalid_reviewer_verdict(
            "Reviewer response must contain score between 0 and 100"
        )

    blocking_issues = data.get("blocking_issues")

    if not isinstance(blocking_issues, list):
        return _invalid_reviewer_verdict(
            "blocking_issues must be an array"
        )

    normalised_issues = []

    for issue in blocking_issues:
        if not isinstance(issue, dict):
            return _invalid_reviewer_verdict(
                "Every blocking issue must be an object"
            )

        title = issue.get("title")
        description = issue.get("description")
        file_path = issue.get("file")

        if not isinstance(title, str) or not title.strip():
            return _invalid_reviewer_verdict(
                "Every blocking issue requires a title"
            )

        if (
            not isinstance(description, str)
            or not description.strip()
        ):
            return _invalid_reviewer_verdict(
                "Every blocking issue requires a description"
            )

        if file_path is not None and not isinstance(file_path, str):
            return _invalid_reviewer_verdict(
                "Blocking issue file must be a string or null"
            )

        normalised_issues.append(
            {
                "title": title.strip(),
                "description": description.strip(),
                "file": file_path.strip()
                if isinstance(file_path, str) and file_path.strip()
                else None,
            }
        )

    feedback = data.get("feedback")

    if not isinstance(feedback, str) or not feedback.strip():
        return _invalid_reviewer_verdict(
            "Reviewer response requires non-empty feedback"
        )

    return {
        "score": score,
        "blocking_issues": normalised_issues,
        "feedback": feedback.strip(),
    }


def elapsed_milliseconds(start: float) -> int:
    """
    Return elapsed monotonic time in milliseconds.
    """
    return int((time.perf_counter() - start) * 1000)


def normalise_usage(usage: Any) -> dict[str, int]:
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


def extract_response_text(
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
