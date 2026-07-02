"""
Together generator client.

This module calls Together.ai chat completions for the generator model.

The generator is expected to return JSON file operations, not prose and
not git patches. The rest of the runtime applies those operations to an
isolated worktree and lets Git produce the real diff.
"""

import os
import time

from dotenv import load_dotenv
from together import Together

load_dotenv()

# TODO:
# Lazily initialise the Together client, like llm_openai.py does, so the
# API can start even when the SDK or API key is missing.
client = Together(api_key=os.getenv("TOGETHER_API_KEY"))

# TODO:
# Add retry/backoff for transient provider failures such as 429 rate limits.
async def call_together(model: str, prompt: str):
    """
    Call a Together-hosted generator model.

    The returned dictionary is provider-normalised so the runner can consume
    text, token counts and duration without depending on Together-specific
    response objects.
    """
    start = time.time()

    # TODO:
    # Move the generator contract prompt to prompt_builder.py or a dedicated
    # provider-agnostic prompt template.
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": """
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
- For create and replace, include the full final file content.
- For delete, omit content.
- Prefer small, focused changes.
""".strip(),
            },
            {"role": "user", "content": prompt},
        ],
        stream=False,
        max_tokens=12000,
        temperature=0.2,
        reasoning={"enabled": False},
    )

    text = response.choices[0].message.content
    usage = getattr(response, "usage", None)

    return {
        "text": text.strip(),
        "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "duration_ms": int((time.time() - start) * 1000),
    }