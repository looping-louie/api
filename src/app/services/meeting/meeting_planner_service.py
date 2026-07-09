"""Build and persist a validated task-specific meeting plan."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.app.personas import load_persona_registry
from src.app.schemas import RunMeetingRequest
from src.app.services.llm_service.prompts import render_prompt
from src.app.services.llm_service.instructions import MEETING_PLANNER_INSTRUCTIONS
from src.app.services.meeting.meeting_artifact_service import get_artifact_contract
from src.app.services.meeting.meeting_runtime_service import UsageTotals, call_json_model
from src.app.services.meeting.meeting_team_service import (
    MAX_CHALLENGERS,
    MAX_PARTICIPANTS,
    MAX_SKILLS_PER_MEMBER,
    MeetingPlan,
    compact_registry,
    index_registry,
    normalise_meeting_plan,
    validate_meeting_constraints,
)
from src.app.skills import load_skill_registry
from src.app.utils.io import write_json, write_text


PERSONA_PLANNER_FIELDS = {
    "id",
    "description",
    "applies_when",
    "applies_to",
    "preferred_skills",
    "default_for",
}

SKILL_PLANNER_FIELDS = {
    "id",
    "description",
    "applies_when",
    "applies_to",
    "reviewer_default_strictness",
}


async def create_meeting_plan(
    *,
    req: RunMeetingRequest,
    usage: UsageTotals,
    run_path: Path,
) -> MeetingPlan:
    """Ask the planner for a team and normalise its untrusted response."""
    persona_registry = load_persona_registry()
    skill_registry = load_skill_registry()
    personas_by_id = index_registry(persona_registry, "persona")
    skills_by_id = index_registry(skill_registry, "skill")
    required_personas = list(dict.fromkeys(req.required_personas))
    required_skills = list(dict.fromkeys(req.required_skills))

    validate_meeting_constraints(
        required_personas=required_personas,
        required_skills=required_skills,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )

    planner_input = _build_planner_input(
        req=req,
        persona_registry=persona_registry,
        skill_registry=skill_registry,
        required_personas=required_personas,
        required_skills=required_skills,
    )
    write_text(run_path, "planner/prompt.txt", planner_input)

    raw_plan, response = await call_json_model(
        model=req.planner_model,
        system_instructions=MEETING_PLANNER_INSTRUCTIONS,
        user_prompt=planner_input,
    )
    usage.add(response)
    write_json(run_path, "planner/response.json", raw_plan)

    plan = normalise_meeting_plan(
        raw_plan=raw_plan,
        required_personas=required_personas,
        required_skills=required_skills,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    write_json(run_path, "meeting-plan.json", asdict(plan))
    return plan


def _build_planner_input(
    *,
    req: RunMeetingRequest,
    persona_registry: list[dict[str, Any]],
    skill_registry: list[dict[str, Any]],
    required_personas: list[str],
    required_skills: list[str],
) -> str:
    """Build the compact dynamic context supplied to the meeting planner."""
    personas = compact_registry(
        persona_registry,
        PERSONA_PLANNER_FIELDS,
    )
    skills = compact_registry(
        skill_registry,
        SKILL_PLANNER_FIELDS,
    )

    planner_prompt = render_prompt(
        "meeting_planner.md",
        meeting_type=req.meeting_type,
        prompt=req.prompt,
        artifact_contract=get_artifact_contract(req.meeting_type),
        constitution=req.constitution,
        required_personas_json=json.dumps(required_personas, ensure_ascii=False),
        required_skills_json=json.dumps(required_skills, ensure_ascii=False),
        max_participants=MAX_PARTICIPANTS,
        max_challengers=MAX_CHALLENGERS,
        max_skills_per_member=MAX_SKILLS_PER_MEMBER,
        personas_json=json.dumps(personas, ensure_ascii=False),
        skills_json=json.dumps(skills, ensure_ascii=False)
    )

    return planner_prompt
