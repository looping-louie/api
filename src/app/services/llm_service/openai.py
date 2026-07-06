import asyncio
import json
import time
from typing import Any
from src.app.skills import load_skill
from .utils import (
    _require_api_key,
    _extract_response_text,
    _parse_reviewer_verdict,
    _normalise_usage,
    _elapsed_milliseconds,
)
from .instructions import (
    REVIEWER_OUTPUT_INSTRUCTIONS,
    SKILL_PLANNER_OUTPUT_INSTRUCTIONS,
)


_openai_client = None


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


async def review_with_openai(
    model: str,
    original_prompt: str,
    candidate_output: str,
    skill: str,
    phase: str,
    strictness: int,
    focus: str,
    constitution: str,
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

        Project phase: {phase}
        Reviewer strictness threshold: {strictness}/100
        Task-specific focus: {focus}

        Project constitution:

        {constitution}

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
        "score": verdict["score"],
        "blocking_issues": verdict["blocking_issues"],
        "feedback": verdict["feedback"],
        **_normalise_usage(usage),
        "duration_ms": _elapsed_milliseconds(start),
    }


async def plan_skills_with_openai(
    *,
    model: str,
    task_prompt: str,
    project_profile: dict[str, Any],
    constitution: str,
    registry: list[dict[str, Any]],
    required_skills: list[str],
    max_reviewers: int,
) -> dict[str, Any]:
    """
    Select the review phase and minimum useful reviewer set.
    """
    client = _get_openai_client()

    # Only expose registry metadata, never complete Markdown skill bodies.
    compact_registry = [
        {
            "id": item["id"],
            "description": item["description"],
            "applies_when": item["applies_when"],
            "default_strictness": item["default_strictness"],
        }
        for item in registry
    ]

    user_prompt = f"""
Task:

{task_prompt}

Repository profile:

{json.dumps(project_profile, ensure_ascii=False)}

Project constitution:

{constitution}

Available skill registry:

{json.dumps(compact_registry, ensure_ascii=False)}

Explicitly required skills:

{json.dumps(required_skills)}

Maximum selected reviewers:

{max_reviewers}
""".strip()

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[
            {
                "role": "system",
                "content": SKILL_PLANNER_OUTPUT_INSTRUCTIONS,
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

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Skill planner returned invalid JSON: {raw}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            "Skill planner response must be a JSON object"
        )

    return data
