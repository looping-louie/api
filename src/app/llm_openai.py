"""
OpenAI reviewer client.

This module executes reviewer skills using the OpenAI Chat Completions API.

Each reviewer receives:
- one review skill;
- the original user request;
- the candidate git diff and changed files.

The model must return a structured JSON verdict that can be aggregated
with the results from other reviewers.
"""

import json
import os
import time

from dotenv import load_dotenv

from src.app.skill_loader import load_skill

load_dotenv()

# Lazily initialised OpenAI client shared by every reviewer invocation.
client = None

def get_client():
    """
    Return the shared OpenAI client.

    The client is created lazily so importing the module does not require a
    valid API key or initialise network resources.
    """
    global client

    if client is None:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60,
            max_retries=1,
        )

    return client


# TODO:
# Make this provider-agnostic.
# The runner should depend on a generic reviewer interface rather than
# directly on an OpenAI implementation.
async def review_with_openai(
    model: str,
    original_prompt: str,
    candidate_output: str,
    skill: str,
):
    """
    Execute one review skill using an OpenAI model.

    The skill Markdown document becomes the system prompt, while the user
    message contains the original task together with the generated diff and
    changed files.

    Returns a provider-normalised review result containing approval state,
    feedback and execution metrics.
    """
    start = time.time()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY")

    skill_prompt = load_skill(skill)

    # TODO:
    # Move the reviewer response contract into prompt_builder.py so every
    # provider shares exactly the same prompt structure.
    response = get_client().chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""
{skill_prompt}

You must return valid JSON only.
The JSON object must include:
- approved: boolean
- feedback: string
""".strip(),
            },
            {
                "role": "user",
                "content": f"""
Return valid JSON only.

Original user prompt:

{original_prompt}

Candidate diff and changed files:

{candidate_output}
""".strip(),
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or ""
    usage = response.usage

    # TODO:
    # Replace this fallback with a shared JSON parser used by every provider.
    # Together and OpenAI currently duplicate JSON parsing behaviour.
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "approved": False,
            "feedback": f"Reviewer returned invalid JSON: {raw}",
        }

    return {
        "approved": bool(data.get("approved", False)),
        "feedback": str(data.get("feedback") or data.get("summary") or raw),
        "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "duration_ms": int((time.time() - start) * 1000),
    }
