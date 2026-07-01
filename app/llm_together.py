import os
import time

from dotenv import load_dotenv
from together import Together

load_dotenv()

client = Together(api_key=os.getenv("TOGETHER_API_KEY"))


async def call_together(model: str, prompt: str):
    start = time.time()

    if not os.getenv("TOGETHER_API_KEY"):
        raise RuntimeError("Missing TOGETHER_API_KEY")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a senior web developer. Return only the requested output.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        stream=False,
        max_tokens=4000,
        temperature=0.3,
        reasoning={"enabled": False},
    )

    text = response.choices[0].message.content
    usage = getattr(response, "usage", None)

    return {
        "text": text,
        "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "duration_ms": int((time.time() - start) * 1000),
    }