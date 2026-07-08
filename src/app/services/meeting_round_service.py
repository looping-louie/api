"""Execution of facilitator, participant, challenger, and validator stages."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.app.schemas import RunMeetingRequest
from src.app.services.llm_service.prompts import render_prompt
from src.app.services.llm_service.instructions import (
    CHALLENGER_INSTRUCTIONS,
    FACILITATOR_AGGREGATION_INSTRUCTIONS,
    FACILITATOR_BRIEF_INSTRUCTIONS,
    PARTICIPANT_INSTRUCTIONS,
    VALIDATOR_INSTRUCTIONS,
)
from src.app.services.meeting_artifact_service import (
    build_round_feedback,
    extract_disagreements,
    get_artifact_contract,
    get_local_contract_issues,
    normalise_artifact,
)
from src.app.services.meeting_team_service import (
    MeetingMember,
    MeetingPlan,
    build_member_instructions,
)
from src.app.services.meeting_runtime_service import (
    UsageTotals,
    call_json_model,
    call_meeting_model,
    strip_code_fence,
)
from src.app.utils.io import write_json, write_text


async def _facilitate_round(
    *,
    req: RunMeetingRequest,
    plan: MeetingPlan,
    round_number: int,
    current_artifact: str,
    previous_feedback: str,
    disagreements: list[str],
    usage: UsageTotals,
    run_path: Path,
) -> dict[str, Any]:
    """
    Ask the facilitator to define the current contribution round.
    """
    facilitator_input = render_prompt(
        "facilitator_input.md",
        prompt=req.prompt,
        artifact_contract=get_artifact_contract(req.meeting_type),
        round_number=round_number,
        current_artifact=current_artifact or "No artifact exists yet.",
        previous_feedback=previous_feedback or "No previous feedback.",
        disagreements_json=json.dumps(disagreements, ensure_ascii=False),
        member_instructions=build_member_instructions(member=plan.facilitator, role="facilitator")
    )
    path = f"rounds/{round_number}/facilitator-brief"
    write_text(run_path, f"{path}-prompt.txt", facilitator_input)
    brief, response = await call_json_model(
        model=req.planner_model,
        system_instructions=FACILITATOR_BRIEF_INSTRUCTIONS,
        user_prompt=facilitator_input,
    )
    usage.add(response)
    write_json(run_path, f"{path}.json", brief)
    return brief


async def _run_participant(
    *,
    req: RunMeetingRequest,
    member: MeetingMember,
    member_index: int,
    round_number: int,
    brief: dict[str, Any],
    current_artifact: str,
    run_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Execute one participant contribution for the current round.
    """
    participant_input = render_prompt(
        "participant_input.md",
        prompt=req.prompt,
        artifact_contract=get_artifact_contract(req.meeting_type),
        current_artifact=current_artifact or "No artifact exists yet.",
        brief_json=json.dumps(brief, ensure_ascii=False),
        member_instructions=build_member_instructions(member=member, role="participant")
    )
    member_key = f"participant-{member_index:02d}-{member.persona}"
    path = f"rounds/{round_number}/{member_key}"
    write_text(run_path, f"{path}-prompt.txt", participant_input)
    contribution, response = await call_json_model(
        model=req.participant_model,
        system_instructions=PARTICIPANT_INSTRUCTIONS,
        user_prompt=participant_input,
    )
    persisted = {
        "persona": member.persona,
        "skills": member.skills,
        "focus": member.focus,
        **contribution,
    }
    write_json(run_path, f"{path}-response.json", persisted)
    return persisted, response


async def _run_participants(
    *,
    req: RunMeetingRequest,
    plan: MeetingPlan,
    round_number: int,
    brief: dict[str, Any],
    current_artifact: str,
    usage: UsageTotals,
    run_path: Path,
) -> list[dict[str, Any]]:
    """
    Execute all participant contributions concurrently.
    """
    results = await asyncio.gather(
        *[
            _run_participant(
                req=req,
                member=member,
                member_index=index,
                round_number=round_number,
                brief=brief,
                current_artifact=current_artifact,
                run_path=run_path,
            )
            for index, member in enumerate(plan.participants, start=1)
        ]
    )

    for _, response in results:
        usage.add(response)

    return [contribution for contribution, _ in results]


async def _aggregate_round(
    *,
    req: RunMeetingRequest,
    plan: MeetingPlan,
    round_number: int,
    brief: dict[str, Any],
    contributions: list[dict[str, Any]],
    current_artifact: str,
    usage: UsageTotals,
    run_path: Path,
) -> dict[str, Any]:
    """
    Consolidate participant contributions and identify disagreements.
    """
    aggregator_input = render_prompt(
        "aggregator_input.md",
        prompt=req.prompt,
        artifact_contract=get_artifact_contract(req.meeting_type),
        current_artifact=current_artifact or "No artifact exists yet.",
        brief_json=json.dumps(brief, ensure_ascii=False),
        contributions_json=json.dumps(contributions, ensure_ascii=False),
        member_instructions=build_member_instructions(member=plan.facilitator, role="facilitator")
    )

    path = f"rounds/{round_number}/facilitator-aggregation"
    write_text(run_path, f"{path}-prompt.txt", aggregator_input)
    aggregation, response = await call_json_model(
        model=req.planner_model,
        system_instructions=FACILITATOR_AGGREGATION_INSTRUCTIONS,
        user_prompt=aggregator_input,
    )
    usage.add(response)
    write_json(run_path, f"{path}.json", aggregation)
    return aggregation


async def _synthesize_artifact(
    *,
    req: RunMeetingRequest,
    plan: MeetingPlan,
    round_number: int,
    aggregation: dict[str, Any],
    current_artifact: str,
    previous_feedback: str,
    usage: UsageTotals,
    run_path: Path,
) -> str:
    """
    Ask the synthesizer to produce the complete artifact for this round.
    """
    synthesizer_input = render_prompt(
        "synthesizer_input.md",
        prompt=req.prompt,
        artifact_contract=get_artifact_contract(req.meeting_type),
        current_artifact=current_artifact or "No artifact exists yet.",
        facilitator_aggregation_json=json.dumps(aggregation, ensure_ascii=False),
        previous_feedback=previous_feedback or "No previous feedback.",
        member_instructions=build_member_instructions(member=plan.synthesizer, role="synthesizer")
    )

    path = f"rounds/{round_number}/synthesizer"
    write_text(run_path, f"{path}-prompt.txt", synthesizer_input)
    response = await call_meeting_model(
        model=req.synthesizer_model,
        prompt=synthesizer_input,
    )
    usage.add(response)
    artifact = strip_code_fence(str(response.get("text", "")))

    artifact = normalise_artifact(
        meeting_type=req.meeting_type,
        artifact=artifact,
    )

    write_text(run_path, f"rounds/{round_number}/artifact.txt", artifact)
    return artifact


async def _run_challenger(
    *,
    req: RunMeetingRequest,
    member: MeetingMember,
    member_index: int,
    round_number: int,
    artifact: str,
    run_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Execute one challenger review against the current artifact.
    """

    challenger_input = render_prompt(
        "challenger_input.md",
        prompt=req.prompt,
        artifact_contract=get_artifact_contract(req.meeting_type),
        artifact=artifact,
        member_instructions=build_member_instructions(member=member, role="challenger"),
        constitution=req.constitution
    )

    member_key = f"challenger-{member_index:02d}-{member.persona}"
    path = f"rounds/{round_number}/{member_key}"
    write_text(run_path, f"{path}-prompt.txt", challenger_input)
    verdict, response = await call_json_model(
        model=req.challenger_model,
        system_instructions=CHALLENGER_INSTRUCTIONS,
        user_prompt=challenger_input,
    )
    score = verdict.get("score", 0)
    blocking_issues = verdict.get("blocking_issues", [])
    feedback = verdict.get("feedback", "")

    if not isinstance(score, int):
        score = 0
    if not isinstance(blocking_issues, list):
        blocking_issues = []
    if not isinstance(feedback, str):
        feedback = ""

    approved = score >= member.strictness and not blocking_issues
    persisted = {
        "persona": member.persona,
        "skills": member.skills,
        "focus": member.focus,
        "strictness": member.strictness,
        "score": max(0, min(100, score)),
        "blocking_issues": blocking_issues,
        "feedback": feedback,
        "approved": approved,
    }
    write_json(run_path, f"{path}-response.json", persisted)
    return persisted, response


async def _run_challengers(
    *,
    req: RunMeetingRequest,
    plan: MeetingPlan,
    round_number: int,
    artifact: str,
    usage: UsageTotals,
    run_path: Path,
) -> list[dict[str, Any]]:
    """
    Execute all challenger reviews concurrently.
    """
    results = await asyncio.gather(
        *[
            _run_challenger(
                req=req,
                member=member,
                member_index=index,
                round_number=round_number,
                artifact=artifact,
                run_path=run_path,
            )
            for index, member in enumerate(plan.challengers, start=1)
        ]
    )

    for _, response in results:
        usage.add(response)

    return [verdict for verdict, _ in results]


async def _validate_artifact(
    *,
    req: RunMeetingRequest,
    plan: MeetingPlan,
    round_number: int,
    artifact: str,
    usage: UsageTotals,
    run_path: Path,
) -> dict[str, Any]:
    """
    Validate the artifact using deterministic and model-based checks.
    """
    local_issues = get_local_contract_issues(
        meeting_type=req.meeting_type,
        artifact=artifact,
    )

    validator_input = render_prompt(
        "validator_input.md",
        prompt=req.prompt,
        artifact_contract=get_artifact_contract(req.meeting_type),
        artifact=artifact,
        issues_json=json.dumps(local_issues, ensure_ascii=False),
        member_instructions=build_member_instructions(member=plan.validator, role="validator")
    )

    path = f"rounds/{round_number}/validator"
    write_text(run_path, f"{path}-prompt.txt", validator_input)
    verdict, response = await call_json_model(
        model=req.challenger_model,
        system_instructions=VALIDATOR_INSTRUCTIONS,
        user_prompt=validator_input,
    )
    usage.add(response)
    model_valid = verdict.get("valid") is True
    model_issues = verdict.get("issues", [])
    feedback = verdict.get("feedback", "")

    if not isinstance(model_issues, list):
        model_issues = []
    if not isinstance(feedback, str):
        feedback = ""

    result = {
        "valid": not local_issues and model_valid,
        "local_issues": local_issues,
        "model_issues": model_issues,
        "feedback": feedback,
    }
    write_json(run_path, f"{path}-response.json", result)
    return result


@dataclass(frozen=True)
class MeetingRoundResult:
    """Complete result and next-round state produced by one meeting round."""

    artifact: str
    feedback: str
    disagreements: list[str]
    approved: bool
    trace: dict[str, Any]


async def execute_meeting_round(
    *,
    req: RunMeetingRequest,
    plan: MeetingPlan,
    round_number: int,
    current_artifact: str,
    previous_feedback: str,
    disagreements: list[str],
    usage: UsageTotals,
    run_path: Path,
) -> MeetingRoundResult:
    """Execute all stages of one meeting round and return its new state."""
    brief = await _facilitate_round(
        req=req,
        plan=plan,
        round_number=round_number,
        current_artifact=current_artifact,
        previous_feedback=previous_feedback,
        disagreements=disagreements,
        usage=usage,
        run_path=run_path,
    )
    contributions = await _run_participants(
        req=req,
        plan=plan,
        round_number=round_number,
        brief=brief,
        current_artifact=current_artifact,
        usage=usage,
        run_path=run_path,
    )
    aggregation = await _aggregate_round(
        req=req,
        plan=plan,
        round_number=round_number,
        brief=brief,
        contributions=contributions,
        current_artifact=current_artifact,
        usage=usage,
        run_path=run_path,
    )
    artifact = await _synthesize_artifact(
        req=req,
        plan=plan,
        round_number=round_number,
        aggregation=aggregation,
        current_artifact=current_artifact,
        previous_feedback=previous_feedback,
        usage=usage,
        run_path=run_path,
    )
    challenger_results = await _run_challengers(
        req=req,
        plan=plan,
        round_number=round_number,
        artifact=artifact,
        usage=usage,
        run_path=run_path,
    )
    validation = await _validate_artifact(
        req=req,
        plan=plan,
        round_number=round_number,
        artifact=artifact,
        usage=usage,
        run_path=run_path,
    )

    approved = (
        all(result.get("approved") is True for result in challenger_results)
        and validation.get("valid") is True
    )
    feedback = build_round_feedback(
        challengers=challenger_results,
        validation=validation,
    )
    next_disagreements = extract_disagreements(aggregation)
    trace = {
        "round": round_number,
        "facilitator_brief": brief,
        "participant_contributions": contributions,
        "facilitator_aggregation": aggregation,
        "artifact": artifact,
        "challengers": challenger_results,
        "validation": validation,
        "feedback_for_next_round": feedback,
        "approved": approved,
    }

    return MeetingRoundResult(
        artifact=artifact,
        feedback=feedback,
        disagreements=next_disagreements,
        approved=approved,
        trace=trace,
    )

