import time

from app.llm_openai import review_with_openai
from app.llm_together import call_together
from app.schemas import Metrics, RunRequest, RunResponse


async def run_harness(req: RunRequest) -> RunResponse:
    start = time.time()
    trace = []
    current_prompt = req.prompt

    total_input_tokens = 0
    total_output_tokens = 0
    final_output = ""

    for iteration in range(1, req.max_iterations + 1):
        gen = await call_together(
            model=req.generator_model,
            prompt=current_prompt,
        )

        review = await review_with_openai(
            model=req.reviewer_model,
            original_prompt=req.prompt,
            candidate_output=gen["text"],
            skill=req.skill,
        )

        iteration_input_tokens = gen["input_tokens"] + review["input_tokens"]
        iteration_output_tokens = gen["output_tokens"] + review["output_tokens"]
        iteration_duration_ms = gen["duration_ms"] + review["duration_ms"]

        total_input_tokens += iteration_input_tokens
        total_output_tokens += iteration_output_tokens

        final_output = gen["text"]

        trace.append(
            {
                "iteration": iteration,
                "generator_output": gen["text"],
                "reviewer_feedback": review["feedback"],
                "approved": review["approved"],
                "input_tokens": iteration_input_tokens,
                "output_tokens": iteration_output_tokens,
                "duration_ms": iteration_duration_ms,
            }
        )

        if review["approved"]:
            break

        current_prompt = f"""
Original user prompt:
{req.prompt}

Previous output:
{gen["text"]}

Reviewer feedback:
{review["feedback"]}

Improve the output. Return only the improved final answer/code.
""".strip()

    duration_ms = int((time.time() - start) * 1000)
    total_tokens = total_input_tokens + total_output_tokens

    return RunResponse(
        final_output=final_output,
        execution_trace=trace,
        metrics=Metrics(
            iterations=len(trace),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            duration_ms=duration_ms,
            tokens_per_second=round(total_tokens / max(duration_ms / 1000, 0.001), 2),
            estimated_cost_eur=0.0,
        ),
    )