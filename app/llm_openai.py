import json
import os
import time

from dotenv import load_dotenv

from app.skill_loader import load_skill

load_dotenv()

client = None


def get_client():
    global client

    if client is None:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60,
            max_retries=1,
        )

    return client


async def review_with_openai(
    model: str,
    original_prompt: str,
    candidate_output: str,
    skill: str,
):
    start = time.time()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY")

    skill_prompt = load_skill(skill)

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