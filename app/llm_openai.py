import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

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
            max_retries=1
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
                "content": skill_prompt,
            },
            {
                "role": "user",
                "content": f"""
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

    raw = response.choices[0].message.content
    data = json.loads(raw)

    usage = response.usage

    return {
        "approved": bool(data.get("approved", False)),
        "feedback": data.get("feedback") or data.get("summary") or raw,
        "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "duration_ms": int((time.time() - start) * 1000),
    }