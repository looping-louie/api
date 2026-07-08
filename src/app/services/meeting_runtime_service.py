"""Shared runtime helpers for structured meetings."""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.app.schemas import RunMeetingRequest, RunMeetingResponse, RunMetrics
from src.app.services.llm_service.openai import call_openai
from src.app.services.llm_service.together import call_together
from src.app.utils.io import write_json, write_text


MEETING_RUNS_DIR = Path(".looping-louie") / "meetings"
OPENAI_MODEL_PREFIXES = ("gpt-", "o1", "o3", "o4")


@dataclass
class UsageTotals:
    """Mutable aggregate of provider-normalised model usage."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0

    def add(self, response: dict[str, Any]) -> None:
        """Add one normalised model response to the aggregate."""
        self.input_tokens += int(response.get("input_tokens", 0))
        self.output_tokens += int(response.get("output_tokens", 0))
        self.cached_input_tokens += int(
            response.get("cached_input_tokens", 0)
        )
        self.reasoning_tokens += int(response.get("reasoning_tokens", 0))


def create_meeting_run(req: RunMeetingRequest) -> tuple[str, Path]:
    """Create one persistent meeting run directory and save its request."""
    run_id = f"meeting-{uuid4().hex[:12]}"
    run_path = MEETING_RUNS_DIR / run_id
    run_path.mkdir(parents=True, exist_ok=False)
    write_json(run_path, "request.json", req.model_dump())
    return run_id, run_path


async def call_meeting_model(
    *,
    model: str,
    prompt: str,
) -> dict[str, Any]:
    """Call a supported provider without generator-specific instructions."""
    if model.startswith(OPENAI_MODEL_PREFIXES):
        return await call_openai(model=model, prompt=prompt)

    return await call_together(
        model,
        prompt,
        system_prompt=None,
    )


def strip_code_fence(value: str) -> str:
    """Remove one accidental Markdown code fence from model output."""
    stripped = value.strip()

    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()

    if len(lines) < 3 or lines[-1].strip() != "```":
        return stripped

    return "\n".join(lines[1:-1]).strip()


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    """Parse one model response as a JSON object."""
    cleaned_text = strip_code_fence(raw_text)

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        raise ValueError(str(exc)) from exc

    if not isinstance(parsed, dict):
        raise ValueError("Model response must be a JSON object")

    return parsed


def _build_json_repair_prompt(
    *,
    invalid_output: str,
    parsing_error: str,
) -> str:
    """Build a prompt that repairs malformed JSON without changing meaning."""
    return f"""
Repair the malformed JSON below.

Return only one valid JSON object.

Rules:
- Preserve the original meaning and values.
- Do not add or remove fields.
- Escape line breaks and quotation marks inside string values.
- Do not include Markdown fences or explanatory prose.

Parser error:

{parsing_error}

Malformed JSON:

{invalid_output}
""".strip()


async def call_json_model(
    *,
    model: str,
    system_instructions: str,
    user_prompt: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Call a model, parse its JSON object, and attempt one repair."""
    prompt = f"{system_instructions}\n\n# Input\n\n{user_prompt}"
    response = await call_meeting_model(model=model, prompt=prompt)
    raw_text = str(response.get("text", ""))

    try:
        return _parse_json_object(raw_text), response
    except ValueError as first_error:
        repair_response = await call_meeting_model(
            model=model,
            prompt=_build_json_repair_prompt(
                invalid_output=raw_text,
                parsing_error=str(first_error),
            ),
        )
        repaired_text = str(repair_response.get("text", ""))

        try:
            parsed = _parse_json_object(repaired_text)
        except ValueError as second_error:
            raise RuntimeError(
                "Model returned invalid JSON and repair failed. "
                f"Initial error: {first_error}. "
                f"Repair error: {second_error}. "
                f"Repaired output: {repaired_text}"
            ) from second_error

        return parsed, _combine_responses(response, repair_response)


def _combine_responses(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    """Combine usage metadata from an initial and repair call."""
    combined = {**second}

    for field in (
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "reasoning_tokens",
        "duration_ms",
    ):
        combined[field] = int(first.get(field, 0)) + int(second.get(field, 0))

    return combined


def build_meeting_response(
    *,
    req: RunMeetingRequest,
    run_id: str,
    final_output: str,
    approved: bool,
    trace: list[dict[str, Any]],
    usage: UsageTotals,
    started_at: float,
) -> RunMeetingResponse:
    """Build the public response and aggregate execution metrics."""
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    total_tokens = usage.input_tokens + usage.output_tokens
    tokens_per_second = round(
        total_tokens / max(duration_ms / 1000, 0.001),
        2,
    )

    return RunMeetingResponse(
        run_id=run_id,
        meeting_type=req.meeting_type,
        final_output=final_output,
        approved=approved,
        run_metrics=RunMetrics(
            iterations=len(trace),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            reasoning_tokens=usage.reasoning_tokens,
            duration_ms=duration_ms,
            tokens_per_second=tokens_per_second,
            estimated_cost_eur=0.0,
        ),
        execution_trace=trace,
    )


def persist_meeting_response(
    *,
    req: RunMeetingRequest,
    run_path: Path,
    response: RunMeetingResponse,
) -> None:
    """Persist the final artifact, response, trace, and metrics."""
    output_name = (
        "idea.md"
        if req.meeting_type == "shape_idea"
        else "tasks.json"
    )
    write_text(run_path, output_name, response.final_output)
    write_json(run_path, "response.json", response.model_dump())
    write_json(run_path, "trace.json", response.execution_trace)
    write_json(
        run_path,
        "metrics.json",
        response.run_metrics.model_dump(),
    )
