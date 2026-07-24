"""Meeting team composition and persona-plus-skill normalisation."""

from dataclasses import dataclass
from typing import Any, Literal, Sequence

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


@dataclass(frozen=True)
class MeetingMember:
    """One persona-plus-skills assignment inside a structured meeting."""

    persona: str
    skills: list[str]
    focus: str
    strictness: int = DEFAULT_CHALLENGER_STRICTNESS


@dataclass(frozen=True)
class MeetingPlan:
    """Normalised composition for one structured meeting."""

    reasoning: str
    participants: list[MeetingMember]
    challengers: list[MeetingMember]
    facilitator: MeetingMember
    validator: MeetingMember
    synthesizer: MeetingMember


def _role_agent_type(role: MeetingRole) -> str:
    """
    Map a meeting role to existing registry compatibility.
    """
    if role in {"participant", "facilitator", "synthesizer"}:
        return "generator"

    return "reviewer"


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


def normalise_meeting_plan(
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
    from .team_requirements import (
        ensure_required_personas,
        ensure_required_skills,
    )

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
    participants, challengers = ensure_required_personas(
        participants=participants,
        challengers=challengers,
        required_personas=required_personas,
        personas_by_id=personas_by_id,
        skills_by_id=skills_by_id,
    )
    participants, challengers = ensure_required_skills(
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


def build_member_instructions(
    *,
    member: MeetingMember,
    role: MeetingRole,
    persona_content: str,
    skill_contents: Sequence[str],
) -> str:
    """
    Assemble already-resolved persona and skill content into instructions.
    """
    persona = persona_content.strip()
    skills = [
        content.strip()
        for content in skill_contents
        if content.strip()
    ]
    sections = [
        f"# Meeting role: {role}",
        "## Persona",
        persona,
    ]

    if skills:
        sections.extend(["## Skills", "\n\n---\n\n".join(skills)])

    sections.extend(["## Task-specific focus", member.focus])
    return "\n\n".join(sections)
