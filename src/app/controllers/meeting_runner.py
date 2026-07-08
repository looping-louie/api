"""
Structured meeting runner.

This module orchestrates multi-persona deliberation sessions that transform an
initial prompt into a constrained, reusable artifact.

A meeting consists of a planner, participants, challengers, a facilitator, a
validator, and a synthesizer. The loop repeats until all challengers approve and
the artifact contract is valid, or until the configured round limit is reached.
"""

import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from src.app.personas import load_persona, load_persona_registry
from src.app.schemas import RunMeetingRequest, RunMeetingResponse, RunMetrics
from src.app.services.llm_service.openai import call_openai
from src.app.services.llm_service.together import call_together
from src.app.services.llm_service.instructions import (
    MEETING_PLANNER_INSTRUCTIONS,
    FACILITATOR_BRIEF_INSTRUCTIONS,
    PARTICIPANT_INSTRUCTIONS,
    FACILITATOR_AGGREGATION_INSTRUCTIONS,
    CHALLENGER_INSTRUCTIONS,
    VALIDATOR_INSTRUCTIONS
)
from src.app.skills import load_skill, load_skill_registry
from src.app.utils.io import write_json, write_text


MeetingRole = Literal[
    "participant",
    "challenger",
    "facilitator",
    "validator",
    "synthesizer",
]

MAX_PARTICIPANTS = 4
MAX_CHALLENGERS = 3
MAX_SKILLS_PER_MEMBER = 3
DEFAULT_CHALLENGER_STRICTNESS = 65
MEETING_RUNS_DIR = Path(".looping-louie") / "meetings"

IDEA_HEADINGS = [
    "## Thesis",
    "## Customer and problem",
    "## Desired outcome",
    "## Proposed solution",
    "## Appetite",
    "## Scope",
    "## Non-goals",
    "## Risks and rabbit holes",
    "## Validation",
    "## Success criteria",
    "## Open decisions",
]

TASK_KEYS = {
    "id",
    "status",
    "prompt",
    "run_id",
    "commit_message",
}


@dataclass(frozen=True)
class MeetingMember:
    """
    One persona-plus-skills assignment inside a structured meeting.

    Challengers use strictness as their approval threshold. Other meeting roles
    retain the field so every assignment has one stable internal shape.
    """

    persona: str
    skills: list[str]
    focus: str
    strictness: int = DEFAULT_CHALLENGER_STRICTNESS


@dataclass(frozen=True)
class MeetingPlan:
    """
    Normalised composition for one structured meeting.

    The plan contains all contributing, challenging, directing, validating, and
    synthesising assignments required by the meeting loop.
    """

    reasoning: str
    participants: list[MeetingMember]
    challengers: list[MeetingMember]
    facilitator: MeetingMember
    validator: MeetingMember
    synthesizer: MeetingMember


@dataclass
class UsageTotals:
    """
    Mutable aggregate of provider-normalised model usage.

    The meeting runner accumulates all model calls into the RunMetrics object
    returned by the API.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0

    def add(self, response: dict[str, Any]) -> None:
        """
        Add one normalised model response to the aggregate.
        """
        self.input_tokens += int(response.get("input_tokens", 0))
        self.output_tokens += int(response.get("output_tokens", 0))
        self.cached_input_tokens += int(
            response.get("cached_input_tokens", 0)
        )
        self.reasoning_tokens += int(response.get("reasoning_tokens", 0))


def _tokens_per_second(
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
) -> float:
    """
    Calculate aggregate token throughput.
    """
    total_tokens = input_tokens + output_tokens
    return round(total_tokens / max(duration_ms / 1000, 0.001), 2)


def _create_run_path() -> tuple[str, Path]:
    """
    Create the persistent directory for one meeting run.
    """
    run_id = f"meeting-{uuid4().hex[:12]}"
    run_path = MEETING_RUNS_DIR / run_id
    run_path.mkdir(parents=True, exist_ok=False)
    return run_id, run_path


def _artifact_contract(meeting_type: str) -> str:
    """
    Return the exact artifact contract for one meeting type.

    Raises:
        ValueError: If the meeting type is not supported.
    """
    if meeting_type == "shape_idea":
        return """
Produce one Markdown document of at most 1000 words.

Use exactly this structure and heading order:

# Idea title

## Thesis
One sentence explaining what should be achieved.

## Customer and problem
Who has the problem, what they are trying to do, and how they solve it today.

## Desired outcome
The observable change the idea should create.

## Proposed solution
The solution concept and primary experience without exhaustive design.

## Appetite
How much effort should be invested and which constraint shapes that decision.

## Scope
What the first version must include.

## Non-goals
What is explicitly excluded.

## Risks and rabbit holes
Assumptions, dependencies, and scope-expansion risks.

## Validation
What must be tested before or during implementation.

## Success criteria
How the team will know the idea works.

## Open decisions
Decisions that still require an answer.

Return the Markdown document only.
""".strip()

    if meeting_type == "plan_implementation":
        return """
Produce valid JSON containing an array of implementation tasks.

Every task must have exactly this shape:

{
  "id": "ideas-001",
  "status": "pending",
  "prompt": "Self-contained implementation instruction with acceptance criteria.",
  "run_id": "",
  "commit_message": "Specific imperative commit message"
}

Rules:
- Return the JSON array only.
- Task ids must be unique and end in a three-digit sequence.
- status must always be "pending".
- run_id must always be an empty string.
- Each task must be independently implementable and reviewable.
- Tasks must be ordered by dependency.
- Each prompt must preserve the approved scope and non-goals.
- Each prompt must include enough context and acceptance criteria to execute
  without reading the meeting transcript.
- Each task should produce one small, coherent commit.
""".strip()

    raise ValueError(f"Unsupported meeting type: {meeting_type}")


def _role_agent_type(role: MeetingRole) -> str:
    """
    Map a meeting role to existing registry compatibility.
    """
    if role in {"participant", "facilitator", "synthesizer"}:
        return "generator"

    return "reviewer"


def _index_registry(
    registry: list[dict[str, Any]],
    entry_type: str,
) -> dict[str, dict[str, Any]]:
    """
    Index registry entries by ID and reject duplicates.
    """
    indexed: dict[str, dict[str, Any]] = {}

    for entry in registry:
        entry_id = entry.get("id")

        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValueError(
                f"{entry_type.title()} registry contains an invalid id"
            )

        if entry_id in indexed:
            raise ValueError(
                f"Duplicate {entry_type} registry id: {entry_id}"
            )

        indexed[entry_id] = entry

    return indexed


def _validate_constraints(
    *,
    required_personas: list[str],
    required_skills: list[str],
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> None:
    """
    Validate user-supplied persona and skill constraints.
    """
    unknown_personas = set(required_personas) - personas_by_id.keys()
    unknown_skills = set(required_skills) - skills_by_id.keys()

    if unknown_personas:
        raise ValueError(
            "Required personas are not present in registry.json: "
            f"{sorted(unknown_personas)}"
        )

    if unknown_skills:
        raise ValueError(
            "Required skills are not present in registry.json: "
            f"{sorted(unknown_skills)}"
        )

    max_people = MAX_PARTICIPANTS + MAX_CHALLENGERS

    if len(set(required_personas)) > max_people:
        raise ValueError(
            f"Required personas exceed meeting capacity of {max_people}"
        )


def _compact_registry(
    registry: list[dict[str, Any]],
    allowed_fields: set[str],
) -> list[dict[str, Any]]:
    """
    Reduce registry metadata to planner-relevant fields.
    """
    return [
        {
            key: value
            for key, value in entry.items()
            if key in allowed_fields
        }
        for entry in registry
    ]


async def _call_model(
    *,
    model: str,
    prompt: str,
) -> dict[str, Any]:
    """
    Call a supported model provider and return a normalised response.
    """
    openai_prefixes = ("gpt-", "o1", "o3", "o4")

    if model.startswith(openai_prefixes):
        return await call_openai(model=model, prompt=prompt)

    return await call_together(model, prompt)


async def _call_json_model(
    *,
    model: str,
    system_instructions: str,
    user_prompt: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Execute a model call that must return one JSON object.
    """
    prompt = f"{system_instructions}\n\n# Input\n\n{user_prompt}"
    response = await _call_model(model=model, prompt=prompt)
    raw_text = _strip_code_fence(str(response.get("text", "")))

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model returned invalid JSON: {raw_text}"
        ) from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("Model response must be a JSON object")

    return parsed, response


def _strip_code_fence(value: str) -> str:
    """
    Remove one accidental Markdown code fence from model output.
    """
    stripped = value.strip()

    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()

    if len(lines) < 3 or lines[-1].strip() != "```":
        return stripped

    return "\n".join(lines[1:-1]).strip()


def _supports_role(
    entry: dict[str, Any] | None,
    role: MeetingRole,
) -> bool:
    """
    Return whether a registry entry supports one meeting role.
    """
    if entry is None:
        return False

    return _role_agent_type(role) in entry.get("applies_to", [])


def _normalise_skill_ids(
    *,
    raw_skills: Any,
    role: MeetingRole,
    skills_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """
    Return unique role-compatible skill IDs within the member limit.
    """
    if not isinstance(raw_skills, list):
        return []

    selected: list[str] = []

    for skill_id in raw_skills:
        if not isinstance(skill_id, str):
            continue
        if skill_id in selected:
            continue
        if not _supports_role(skills_by_id.get(skill_id), role):
            continue

        selected.append(skill_id)

        if len(selected) == MAX_SKILLS_PER_MEMBER:
            break

    return selected


def _default_strictness(
    *,
    skill_ids: list[str],
    skills_by_id: dict[str, dict[str, Any]],
) -> int:
    """
    Derive challenger strictness from assigned skill defaults.
    """
    defaults = []

    for skill_id in skill_ids:
        strictness = skills_by_id[skill_id].get(
            "reviewer_default_strictness",
            {},
        )
        value = strictness.get("mvp", DEFAULT_CHALLENGER_STRICTNESS)

        if isinstance(value, int):
            defaults.append(value)

    return max(defaults, default=DEFAULT_CHALLENGER_STRICTNESS)


def _normalise_member(
    *,
    raw_member: Any,
    role: MeetingRole,
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> MeetingMember | None:
    """
    Convert one untrusted planner assignment into a valid meeting member.
    """
    if not isinstance(raw_member, dict):
        return None

    persona_id = raw_member.get("persona")

    if not isinstance(persona_id, str):
        return None

    if not _supports_role(personas_by_id.get(persona_id), role):
        return None

    skill_ids = _normalise_skill_ids(
        raw_skills=raw_member.get("skills"),
        role=role,
        skills_by_id=skills_by_id,
    )
    focus = raw_member.get("focus")

    if not isinstance(focus, str) or not focus.strip():
        focus = personas_by_id[persona_id]["description"]

    strictness = raw_member.get("strictness")
    default = _default_strictness(
        skill_ids=skill_ids,
        skills_by_id=skills_by_id,
    )

    if not isinstance(strictness, int):
        strictness = default

    return MeetingMember(
        persona=persona_id,
        skills=skill_ids,
        focus=focus.strip(),
        strictness=max(0, min(100, strictness)),
    )


def _normalise_member_list(
    *,
    raw_members: Any,
    role: Literal["participant", "challenger"],
    limit: int,
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> list[MeetingMember]:
    """
    Normalise one participant or challenger list.
    """
    if not isinstance(raw_members, list):
        return []

    members: list[MeetingMember] = []
    seen_personas: set[str] = set()

    for raw_member in raw_members:
        member = _normalise_member(
            raw_member=raw_member,
            role=role,
            personas_by_id=personas_by_id,
            skills_by_id=skills_by_id,
        )

        if member is None or member.persona in seen_personas:
            continue

        if role == "challenger" and not member.skills:
            continue

        members.append(member)
        seen_personas.add(member.persona)

        if len(members) == limit:
            break

    return members


def _select_persona(
    *,
    role: MeetingRole,
    personas_by_id: dict[str, dict[str, Any]],
    preferred_ids: list[str],
) -> str:
    """
    Select a deterministic role-compatible fallback persona.
    """
    for persona_id in preferred_ids:
        if _supports_role(personas_by_id.get(persona_id), role):
            return persona_id

    for persona_id, entry in personas_by_id.items():
        if _supports_role(entry, role):
            return persona_id

    raise RuntimeError(f"No persona supports meeting role: {role}")


def _select_skill(
    *,
    role: MeetingRole,
    skills_by_id: dict[str, dict[str, Any]],
    preferred_ids: list[str],
) -> str:
    """
    Select one deterministic role-compatible fallback skill.
    """
    for skill_id in preferred_ids:
        if _supports_role(skills_by_id.get(skill_id), role):
            return skill_id

    for skill_id, entry in skills_by_id.items():
        if _supports_role(entry, role):
            return skill_id

    raise RuntimeError(f"No skill supports meeting role: {role}")


def _fallback_member(
    *,
    role: MeetingRole,
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> MeetingMember:
    """
    Build a deterministic specialist fallback for one meeting role.
    """
    persona_preferences = {
        "participant": ["product_manager", "tech_lead", "ux_designer"],
        "challenger": [
            "devils_advocate",
            "tech_lead",
            "enterprise_customer",
        ],
        "facilitator": ["product_manager", "tech_lead"],
        "validator": ["tech_lead", "devils_advocate"],
        "synthesizer": ["editor", "product_manager"],
    }
    skill_preferences = {
        "participant": [
            "idea_shaping",
            "customer_problem",
            "web_development",
        ],
        "challenger": [
            "risk_analysis",
            "resilience",
            "web_development",
        ],
        "facilitator": [
            "idea_shaping",
            "task_decomposition",
            "web_development",
        ],
        "validator": [
            "acceptance_criteria",
            "task_decomposition",
            "web_development",
        ],
        "synthesizer": [
            "idea_shaping",
            "task_decomposition",
            "web_development",
        ],
    }

    persona_id = _select_persona(
        role=role,
        personas_by_id=personas_by_id,
        preferred_ids=persona_preferences[role],
    )
    skill_id = _select_skill(
        role=role,
        skills_by_id=skills_by_id,
        preferred_ids=skill_preferences[role],
    )

    return MeetingMember(
        persona=persona_id,
        skills=[skill_id],
        focus=personas_by_id[persona_id]["description"],
        strictness=_default_strictness(
            skill_ids=[skill_id],
            skills_by_id=skills_by_id,
        ),
    )


def _ensure_required_personas(
    *,
    participants: list[MeetingMember],
    challengers: list[MeetingMember],
    required_personas: list[str],
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> tuple[list[MeetingMember], list[MeetingMember]]:
    """
    Guarantee that every user-required persona participates in the meeting.
    """
    assigned = {
        member.persona
        for member in [*participants, *challengers]
    }

    for persona_id in dict.fromkeys(required_personas):
        if persona_id in assigned:
            continue

        entry = personas_by_id[persona_id]

        if (
            "generator" in entry.get("applies_to", [])
            and len(participants) < MAX_PARTICIPANTS
        ):
            participants.append(
                MeetingMember(
                    persona=persona_id,
                    skills=[],
                    focus=entry["description"],
                )
            )
            assigned.add(persona_id)
            continue

        if (
            "reviewer" in entry.get("applies_to", [])
            and len(challengers) < MAX_CHALLENGERS
        ):
            preferred_skills = [
                skill_id
                for skill_id in entry.get("preferred_skills", [])
                if _supports_role(skills_by_id.get(skill_id), "challenger")
            ][:MAX_SKILLS_PER_MEMBER]

            if not preferred_skills:
                preferred_skills = [
                    _select_skill(
                        role="challenger",
                        skills_by_id=skills_by_id,
                        preferred_ids=[],
                    )
                ]

            challengers.append(
                MeetingMember(
                    persona=persona_id,
                    skills=preferred_skills,
                    focus=entry["description"],
                    strictness=_default_strictness(
                        skill_ids=preferred_skills,
                        skills_by_id=skills_by_id,
                    ),
                )
            )
            assigned.add(persona_id)
            continue

        raise RuntimeError(
            "Could not place required persona within meeting limits: "
            f"{persona_id}"
        )

    return participants, challengers


def _append_required_skill(
    *,
    members: list[MeetingMember],
    role: Literal["participant", "challenger"],
    skill_id: str,
    skills_by_id: dict[str, dict[str, Any]],
) -> bool:
    """
    Append a required skill to the first compatible member with capacity.
    """
    if not _supports_role(skills_by_id.get(skill_id), role):
        return False

    for index, member in enumerate(members):
        if len(member.skills) >= MAX_SKILLS_PER_MEMBER:
            continue

        updated_skills = [*member.skills, skill_id]
        members[index] = MeetingMember(
            persona=member.persona,
            skills=updated_skills,
            focus=member.focus,
            strictness=max(
                member.strictness,
                _default_strictness(
                    skill_ids=updated_skills,
                    skills_by_id=skills_by_id,
                ),
            ),
        )
        return True

    return False


def _member_for_required_skill(
    *,
    role: Literal["participant", "challenger"],
    skill_id: str,
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> MeetingMember:
    """
    Create a compatible member for one unassigned required skill.
    """
    preferred_personas = [
        persona_id
        for persona_id, entry in personas_by_id.items()
        if skill_id in entry.get("preferred_skills", [])
        and _supports_role(entry, role)
    ]
    persona_id = _select_persona(
        role=role,
        personas_by_id=personas_by_id,
        preferred_ids=preferred_personas,
    )

    return MeetingMember(
        persona=persona_id,
        skills=[skill_id],
        focus=skills_by_id[skill_id]["description"],
        strictness=_default_strictness(
            skill_ids=[skill_id],
            skills_by_id=skills_by_id,
        ),
    )


def _ensure_required_skills(
    *,
    participants: list[MeetingMember],
    challengers: list[MeetingMember],
    required_skills: list[str],
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> tuple[list[MeetingMember], list[MeetingMember]]:
    """
    Guarantee that every required skill is assigned.
    """
    assigned = {
        skill_id
        for member in [*participants, *challengers]
        for skill_id in member.skills
    }

    for skill_id in dict.fromkeys(required_skills):
        if skill_id in assigned:
            continue

        if _append_required_skill(
            members=participants,
            role="participant",
            skill_id=skill_id,
            skills_by_id=skills_by_id,
        ):
            assigned.add(skill_id)
            continue

        if _append_required_skill(
            members=challengers,
            role="challenger",
            skill_id=skill_id,
            skills_by_id=skills_by_id,
        ):
            assigned.add(skill_id)
            continue

        entry = skills_by_id[skill_id]
        role: Literal["participant", "challenger"]
        role = (
            "participant"
            if "generator" in entry.get("applies_to", [])
            else "challenger"
        )
        member = _member_for_required_skill(
            role=role,
            skill_id=skill_id,
            personas_by_id=personas_by_id,
            skills_by_id=skills_by_id,
        )

        if role == "participant" and len(participants) < MAX_PARTICIPANTS:
            participants.append(member)
            assigned.add(skill_id)
            continue

        if role == "challenger" and len(challengers) < MAX_CHALLENGERS:
            challengers.append(member)
            assigned.add(skill_id)
            continue

        raise RuntimeError(
            "Could not assign required skill within meeting limits: "
            f"{skill_id}"
        )

    return participants, challengers


def _normalise_meeting_plan(
    *,
    raw_plan: dict[str, Any],
    required_personas: list[str],
    required_skills: list[str],
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> MeetingPlan:
    """
    Convert untrusted planner output into a complete valid meeting plan.
    """
    participants = _normalise_member_list(
        raw_members=raw_plan.get("participants"),
        role="participant",
        limit=MAX_PARTICIPANTS,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    challengers = _normalise_member_list(
        raw_members=raw_plan.get("challengers"),
        role="challenger",
        limit=MAX_CHALLENGERS,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    participants, challengers = _ensure_required_personas(
        participants=participants,
        challengers=challengers,
        required_personas=required_personas,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    participants, challengers = _ensure_required_skills(
        participants=participants,
        challengers=challengers,
        required_skills=required_skills,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )

    if not participants:
        participants = [
            _fallback_member(
                role="participant",
                personas_by_id=personas_by_id,
                skills_by_id=skills_by_id,
            )
        ]

    if not challengers:
        challengers = [
            _fallback_member(
                role="challenger",
                personas_by_id=personas_by_id,
                skills_by_id=skills_by_id,
            )
        ]

    facilitator = _normalise_member(
        raw_member=raw_plan.get("facilitator"),
        role="facilitator",
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    validator = _normalise_member(
        raw_member=raw_plan.get("validator"),
        role="validator",
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    synthesizer = _normalise_member(
        raw_member=raw_plan.get("synthesizer"),
        role="synthesizer",
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    reasoning = raw_plan.get("reasoning")

    if not isinstance(reasoning, str) or not reasoning.strip():
        reasoning = "Planner did not provide reasoning."

    return MeetingPlan(
        reasoning=reasoning.strip(),
        participants=participants,
        challengers=challengers,
        facilitator=facilitator
        or _fallback_member(
            role="facilitator",
            personas_by_id=personas_by_id,
            skills_by_id=skills_by_id,
        ),
        validator=validator
        or _fallback_member(
            role="validator",
            personas_by_id=personas_by_id,
            skills_by_id=skills_by_id,
        ),
        synthesizer=synthesizer
        or _fallback_member(
            role="synthesizer",
            personas_by_id=personas_by_id,
            skills_by_id=skills_by_id,
        ),
    )


async def _create_meeting_plan(
    *,
    req: RunMeetingRequest,
    persona_registry: list[dict[str, Any]],
    skill_registry: list[dict[str, Any]],
    usage: UsageTotals,
    run_path: Path,
) -> MeetingPlan:
    """
    Ask the planner for a task-specific team and normalise its output.
    """
    personas_by_id = _index_registry(persona_registry, "persona")
    skills_by_id = _index_registry(skill_registry, "skill")
    required_personas = list(dict.fromkeys(req.required_personas))
    required_skills = list(dict.fromkeys(req.required_skills))

    _validate_constraints(
        required_personas=required_personas,
        required_skills=required_skills,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )

    persona_fields = {
        "id",
        "description",
        "applies_when",
        "applies_to",
        "preferred_skills",
        "default_for",
    }
    skill_fields = {
        "id",
        "description",
        "applies_when",
        "applies_to",
        "reviewer_default_strictness",
    }
    planner_input = f"""
Meeting type:

{req.meeting_type}

Initial prompt or source artifact:

{req.prompt}

Artifact contract:

{_artifact_contract(req.meeting_type)}

Project constitution:

{req.constitution}

Required personas:

{json.dumps(required_personas, ensure_ascii=False)}

Required skills:

{json.dumps(required_skills, ensure_ascii=False)}

Maximum participants: {MAX_PARTICIPANTS}
Maximum challengers: {MAX_CHALLENGERS}
Maximum skills per member: {MAX_SKILLS_PER_MEMBER}

Persona registry:

{json.dumps(_compact_registry(persona_registry, persona_fields), ensure_ascii=False)}

Skill registry:

{json.dumps(_compact_registry(skill_registry, skill_fields), ensure_ascii=False)}
""".strip()

    write_text(run_path, "planner/prompt.txt", planner_input)
    raw_plan, response = await _call_json_model(
        model=req.planner_model,
        system_instructions=MEETING_PLANNER_INSTRUCTIONS,
        user_prompt=planner_input,
    )
    usage.add(response)
    write_json(run_path, "planner/response.json", raw_plan)

    plan = _normalise_meeting_plan(
        raw_plan=raw_plan,
        required_personas=required_personas,
        required_skills=required_skills,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    write_json(run_path, "meeting-plan.json", asdict(plan))
    return plan


def _member_instructions(
    *,
    member: MeetingMember,
    role: MeetingRole,
) -> str:
    """
    Assemble one persona and its assigned skills into model instructions.
    """
    persona = load_persona(member.persona).strip()
    skills = [load_skill(skill_id).strip() for skill_id in member.skills]
    sections = [
        f"# Meeting role: {role}",
        "## Persona",
        persona,
    ]

    if skills:
        sections.extend(["## Skills", "\n\n---\n\n".join(skills)])

    sections.extend(["## Task-specific focus", member.focus])
    return "\n\n".join(sections)


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
    facilitator_input = f"""
Original prompt:

{req.prompt}

Artifact contract:

{_artifact_contract(req.meeting_type)}

Round number: {round_number}

Current artifact:

{current_artifact or "No artifact exists yet."}

Previous challenge and validation feedback:

{previous_feedback or "No previous feedback."}

Known disagreements:

{json.dumps(disagreements, ensure_ascii=False)}

Facilitator assignment:

{_member_instructions(member=plan.facilitator, role="facilitator")}
""".strip()

    path = f"rounds/{round_number}/facilitator-brief"
    write_text(run_path, f"{path}-prompt.txt", facilitator_input)
    brief, response = await _call_json_model(
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
    participant_input = f"""
Original prompt:

{req.prompt}

Artifact contract:

{_artifact_contract(req.meeting_type)}

Current artifact:

{current_artifact or "No artifact exists yet."}

Facilitator brief:

{json.dumps(brief, ensure_ascii=False)}

Participant assignment:

{_member_instructions(member=member, role="participant")}
""".strip()

    member_key = f"participant-{member_index:02d}-{member.persona}"
    path = f"rounds/{round_number}/{member_key}"
    write_text(run_path, f"{path}-prompt.txt", participant_input)
    contribution, response = await _call_json_model(
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
    aggregation_input = f"""
Original prompt:

{req.prompt}

Artifact contract:

{_artifact_contract(req.meeting_type)}

Current artifact:

{current_artifact or "No artifact exists yet."}

Facilitator brief:

{json.dumps(brief, ensure_ascii=False)}

Participant contributions:

{json.dumps(contributions, ensure_ascii=False)}

Facilitator assignment:

{_member_instructions(member=plan.facilitator, role="facilitator")}
""".strip()

    path = f"rounds/{round_number}/facilitator-aggregation"
    write_text(run_path, f"{path}-prompt.txt", aggregation_input)
    aggregation, response = await _call_json_model(
        model=req.planner_model,
        system_instructions=FACILITATOR_AGGREGATION_INSTRUCTIONS,
        user_prompt=aggregation_input,
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
    synthesizer_input = f"""
Write the complete artifact now.

Original prompt or source artifact:

{req.prompt}

Artifact contract:

{_artifact_contract(req.meeting_type)}

Current artifact:

{current_artifact or "No artifact exists yet."}

Facilitator aggregation:

{json.dumps(aggregation, ensure_ascii=False)}

Previous challenge and validation feedback:

{previous_feedback or "No previous feedback."}

Synthesizer assignment:

{_member_instructions(member=plan.synthesizer, role="synthesizer")}

Return the artifact only. Do not include commentary or code fences.
""".strip()

    path = f"rounds/{round_number}/synthesizer"
    write_text(run_path, f"{path}-prompt.txt", synthesizer_input)
    response = await _call_model(
        model=req.synthesizer_model,
        prompt=synthesizer_input,
    )
    usage.add(response)
    artifact = _strip_code_fence(str(response.get("text", "")))

    if req.meeting_type == "plan_implementation":
        artifact = _normalise_tasks_json(artifact)

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
    challenger_input = f"""
Original prompt:

{req.prompt}

Artifact contract:

{_artifact_contract(req.meeting_type)}

Candidate artifact:

{artifact}

Challenger assignment:

{_member_instructions(member=member, role="challenger")}

Project constitution:

{req.constitution}
""".strip()

    member_key = f"challenger-{member_index:02d}-{member.persona}"
    path = f"rounds/{round_number}/{member_key}"
    write_text(run_path, f"{path}-prompt.txt", challenger_input)
    verdict, response = await _call_json_model(
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


def _validate_idea_markdown(artifact: str) -> list[str]:
    """
    Validate the deterministic structure and length of an idea artifact.
    """
    issues: list[str] = []
    lines = [
        line.strip()
        for line in artifact.splitlines()
        if line.strip()
    ]

    if not lines or not re.fullmatch(r"# [^#].+", lines[0]):
        issues.append(
            "The artifact must start with one non-empty H1 idea title."
        )

    actual_headings = [line for line in lines if line.startswith("## ")]

    if actual_headings != IDEA_HEADINGS:
        issues.append(
            "The H2 headings must exactly match the required order."
        )

    word_count = len(re.findall(r"\b[\w'-]+\b", artifact))

    if word_count > 1000:
        issues.append(
            f"The idea artifact contains {word_count} words; maximum is 1000."
        )

    return issues


def _normalise_tasks_json(artifact: str) -> str:
    """
    Parse and pretty-print a tasks JSON artifact when valid.
    """
    try:
        data = json.loads(artifact)
    except json.JSONDecodeError:
        return artifact.strip()

    return json.dumps(data, ensure_ascii=False, indent=2)


def _validate_task_id(
    *,
    task_id: Any,
    prefix: str,
    seen_ids: set[str],
) -> list[str]:
    """
    Validate one task identifier and update the duplicate tracker.
    """
    if (
        not isinstance(task_id, str)
        or not re.fullmatch(r"[a-z][a-z0-9-]*-\d{3}", task_id)
    ):
        return [f"{prefix} id must end in a three-digit sequence."]

    if task_id in seen_ids:
        return [f"{prefix} id is duplicated: {task_id}."]

    seen_ids.add(task_id)
    return []


def _validate_task_item(
    *,
    item: Any,
    index: int,
    seen_ids: set[str],
) -> list[str]:
    """
    Validate one task object against the stable tasks.json contract.
    """
    prefix = f"Task {index}"

    if not isinstance(item, dict):
        return [f"{prefix} must be a JSON object."]

    issues = []

    if set(item.keys()) != TASK_KEYS:
        issues.append(
            f"{prefix} must contain exactly {sorted(TASK_KEYS)}."
        )

    issues.extend(
        _validate_task_id(
            task_id=item.get("id"),
            prefix=prefix,
            seen_ids=seen_ids,
        )
    )

    if item.get("status") != "pending":
        issues.append(f"{prefix} status must be 'pending'.")

    if item.get("run_id") != "":
        issues.append(f"{prefix} run_id must be an empty string.")

    prompt = item.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        issues.append(f"{prefix} prompt must be a non-empty string.")

    commit_message = item.get("commit_message")
    if not isinstance(commit_message, str) or not commit_message.strip():
        issues.append(f"{prefix} commit_message must be non-empty.")

    return issues


def _validate_tasks_json(artifact: str) -> list[str]:
    """
    Validate the deterministic schema of a tasks artifact.
    """
    try:
        data = json.loads(artifact)
    except json.JSONDecodeError as exc:
        return [f"The tasks artifact is not valid JSON: {exc}"]

    if not isinstance(data, list):
        return ["The tasks artifact must be a JSON array."]

    if not data:
        return ["The tasks artifact must contain at least one task."]

    issues: list[str] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(data, start=1):
        issues.extend(
            _validate_task_item(
                item=item,
                index=index,
                seen_ids=seen_ids,
            )
        )

    return issues


def _local_contract_issues(
    *,
    meeting_type: str,
    artifact: str,
) -> list[str]:
    """
    Run deterministic validation for the selected artifact type.
    """
    if meeting_type == "shape_idea":
        return _validate_idea_markdown(artifact)

    if meeting_type == "plan_implementation":
        return _validate_tasks_json(artifact)

    return [f"Unsupported meeting type: {meeting_type}"]


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
    local_issues = _local_contract_issues(
        meeting_type=req.meeting_type,
        artifact=artifact,
    )
    validator_input = f"""
Original prompt:

{req.prompt}

Artifact contract:

{_artifact_contract(req.meeting_type)}

Candidate artifact:

{artifact}

Deterministic validation issues:

{json.dumps(local_issues, ensure_ascii=False)}

Validator assignment:

{_member_instructions(member=plan.validator, role="validator")}
""".strip()

    path = f"rounds/{round_number}/validator"
    write_text(run_path, f"{path}-prompt.txt", validator_input)
    verdict, response = await _call_json_model(
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


def _round_feedback(
    *,
    challengers: list[dict[str, Any]],
    validation: dict[str, Any],
) -> str:
    """
    Consolidate challenger and validator feedback for the next round.
    """
    sections = []

    for challenger in challengers:
        if challenger.get("approved"):
            continue

        skills = ", ".join(challenger.get("skills", []))
        sections.append(
            (
                f"Challenger {challenger.get('persona')} ({skills}) scored "
                f"{challenger.get('score')} against "
                f"{challenger.get('strictness')}.\n"
                f"Blocking issues: "
                f"{json.dumps(challenger.get('blocking_issues', []), ensure_ascii=False)}\n"
                f"Feedback: {challenger.get('feedback', '')}"
            )
        )

    if not validation.get("valid"):
        sections.append(
            (
                "Validator rejected the artifact.\n"
                f"Local issues: "
                f"{json.dumps(validation.get('local_issues', []), ensure_ascii=False)}\n"
                f"Model issues: "
                f"{json.dumps(validation.get('model_issues', []), ensure_ascii=False)}\n"
                f"Feedback: {validation.get('feedback', '')}"
            )
        )

    return "\n\n".join(sections)


def _extract_disagreements(
    aggregation: dict[str, Any],
) -> list[str]:
    """
    Extract a clean list of disagreements from facilitator output.
    """
    disagreements = aggregation.get("disagreements", [])

    if not isinstance(disagreements, list):
        return []

    return [
        item.strip()
        for item in disagreements
        if isinstance(item, str) and item.strip()
    ]


async def run_meeting(
    req: RunMeetingRequest,
) -> RunMeetingResponse:
    """
    Execute one structured multi-persona meeting.

    The meeting planner assigns skills to user-selected personas and divides
    them between participants and challengers. Each contribution round is
    directed by a facilitator, consolidated into a candidate artifact, reviewed
    by challengers, and checked by a validator.

    The loop stops when every challenger approves and the artifact contract is
    valid, or after the requested number of rounds. The synthesizer's latest
    complete artifact is always returned.

    Args:
        req:
            Meeting prompt or source artifact, meeting type, model selection,
            round limit, optional persona and skill constraints, and project
            constitution.

    Returns:
        The final artifact, approval state, complete execution trace, and
        aggregate model usage metrics.
    """
    start = time.time()
    run_id, run_path = _create_run_path()
    usage = UsageTotals()

    write_json(run_path, "request.json", req.model_dump())

    persona_registry = load_persona_registry()
    skill_registry = load_skill_registry()
    plan = await _create_meeting_plan(
        req=req,
        persona_registry=persona_registry,
        skill_registry=skill_registry,
        usage=usage,
        run_path=run_path,
    )

    trace: list[dict[str, Any]] = []
    current_artifact = ""
    previous_feedback = ""
    disagreements: list[str] = []
    approved = False

    for round_number in range(1, req.max_iterations + 1):
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
        current_artifact = await _synthesize_artifact(
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
            artifact=current_artifact,
            usage=usage,
            run_path=run_path,
        )
        validation = await _validate_artifact(
            req=req,
            plan=plan,
            round_number=round_number,
            artifact=current_artifact,
            usage=usage,
            run_path=run_path,
        )

        challengers_approved = all(
            result.get("approved") is True
            for result in challenger_results
        )
        approved = challengers_approved and validation.get("valid") is True
        previous_feedback = _round_feedback(
            challengers=challenger_results,
            validation=validation,
        )
        disagreements = _extract_disagreements(aggregation)

        trace.append(
            {
                "round": round_number,
                "facilitator_brief": brief,
                "participant_contributions": contributions,
                "facilitator_aggregation": aggregation,
                "artifact": current_artifact,
                "challengers": challenger_results,
                "validation": validation,
                "feedback_for_next_round": previous_feedback,
                "approved": approved,
            }
        )

        if approved:
            break

    duration_ms = int((time.time() - start) * 1000)
    response = RunMeetingResponse(
        run_id=run_id,
        meeting_type=req.meeting_type,
        final_output=current_artifact,
        approved=approved,
        run_metrics=RunMetrics(
            iterations=len(trace),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            reasoning_tokens=usage.reasoning_tokens,
            duration_ms=duration_ms,
            tokens_per_second=_tokens_per_second(
                usage.input_tokens,
                usage.output_tokens,
                duration_ms,
            ),
            estimated_cost_eur=0.0,
        ),
        execution_trace=trace,
    )

    output_name = (
        "idea.md"
        if req.meeting_type == "shape_idea"
        else "tasks.json"
    )
    write_text(run_path, output_name, current_artifact)
    write_json(run_path, "response.json", response.model_dump())
    write_json(run_path, "trace.json", trace)
    write_json(run_path, "metrics.json", response.run_metrics.model_dump())

    return response
