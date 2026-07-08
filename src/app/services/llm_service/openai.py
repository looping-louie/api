"""
OpenAI model client.

This module executes reviewer assignments and creates execution plans using
OpenAI chat completions. Provider responses are normalised before returning
to the orchestration layer.
"""

import asyncio
import json
import time
from typing import Any

from .instructions import (
    EXECUTION_PLANNER_OUTPUT_INSTRUCTIONS,
    REVIEWER_OUTPUT_INSTRUCTIONS,
)
from .utils import (
    elapsed_milliseconds,
    extract_response_text,
    normalise_usage,
    parse_reviewer_verdict,
    require_api_key,
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
        api_key = require_api_key(
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
    *,
    model: str,
    original_prompt: str,
    candidate_output: str,
    reviewer_instructions: str,
    phase: str,
    strictness: int,
    focus: str,
    constitution: str,
) -> dict[str, Any]:
    """
    Execute one persona-plus-skills reviewer assignment.

    The caller provides already assembled reviewer instructions containing the
    selected persona and all assigned skills. This service only adds execution
    metadata, the project constitution, and the output contract.

    The synchronous provider SDK is executed in a worker thread so it does not
    block the application's asynchronous event loop.
    """
    start = time.perf_counter()
    client = _get_openai_client()

    system_prompt = f"""
{reviewer_instructions}

# Review context

Project phase: {phase}
Reviewer strictness threshold: {strictness}/100
Task-specific focus: {focus}

Project constitution:

{constitution}

# Output contract

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

    raw = extract_response_text(
        response=response,
        provider_name="OpenAI",
    )
    verdict = parse_reviewer_verdict(raw)
    usage = getattr(response, "usage", None)

    return {
        "score": verdict["score"],
        "blocking_issues": verdict["blocking_issues"],
        "feedback": verdict["feedback"],
        **normalise_usage(usage),
        "duration_ms": elapsed_milliseconds(start),
    }


async def plan_execution_with_openai(
    *,
    model: str,
    task_prompt: str,
    project_profile: dict[str, Any],
    constitution: str,
    skill_registry: list[dict[str, Any]],
    persona_registry: list[dict[str, Any]],
    required_skills: list[str],
    generator_persona: str | None,
    max_reviewers: int,
    max_generator_skills: int,
    max_skills_per_reviewer: int,
) -> dict[str, Any]:
    """
    Select the project phase, generator assignment, and reviewer team.

    Only compact registry metadata is exposed to the planner. Complete persona
    and skill Markdown bodies are loaded later when the harness assembles each
    model prompt.
    """
    client = _get_openai_client()

    compact_skill_registry = [
        {
            "id": item["id"],
            "description": item["description"],
            "applies_when": item["applies_when"],
            "applies_to": item["applies_to"],
            "reviewer_default_strictness": (
                item["reviewer_default_strictness"]
            ),
        }
        for item in skill_registry
    ]
    compact_persona_registry = [
        {
            "id": item["id"],
            "description": item["description"],
            "applies_when": item["applies_when"],
            "applies_to": item["applies_to"],
            "preferred_skills": item["preferred_skills"],
            "default_for": item["default_for"],
        }
        for item in persona_registry
    ]

    user_prompt = f"""
Task:

{task_prompt}

Repository profile:

{json.dumps(project_profile, ensure_ascii=False)}

Project constitution:

{constitution}

Available skill registry:

{json.dumps(compact_skill_registry, ensure_ascii=False)}

Available persona registry:

{json.dumps(compact_persona_registry, ensure_ascii=False)}

Explicitly required reviewer skills:

{json.dumps(required_skills, ensure_ascii=False)}

Fixed generator persona:

{json.dumps(generator_persona, ensure_ascii=False)}

Maximum selected reviewers:

{max_reviewers}

Maximum generator skills:

{max_generator_skills}

Maximum skills per reviewer:

{max_skills_per_reviewer}
""".strip()

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[
            {
                "role": "system",
                "content": EXECUTION_PLANNER_OUTPUT_INSTRUCTIONS,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = extract_response_text(
        response=response,
        provider_name="OpenAI",
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Execution planner returned invalid JSON: {raw}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            "Execution planner response must be a JSON object"
        )

    return data
