# app/llm_openai.py
import time

from app.skill_loader import load_skill

async def review_with_openai(
    model: str,
    original_prompt: str,
    candidate_output: str,
    skill: str,
):
    start = time.time()

    feedback = "Fake review approved."

    return {
        "approved": True,
        "feedback": feedback,
        "input_tokens": len((original_prompt + candidate_output).split()),
        "output_tokens": len(feedback.split()),
        "duration_ms": int((time.time() - start) * 1000),
    }