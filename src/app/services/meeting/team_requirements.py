"""Required persona and skill placement for normalized meeting teams."""

from typing import Any, Literal

from .team import (
    MAX_CHALLENGERS,
    MAX_PARTICIPANTS,
    MAX_SKILLS_PER_MEMBER,
    MeetingMember,
    _default_strictness,
    _select_persona,
    _select_skill,
    _supports_role,
)


def ensure_required_personas(
    *,
    participants: list[MeetingMember],
    challengers: list[MeetingMember],
    required_personas: list[str],
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> tuple[list[MeetingMember], list[MeetingMember]]:
    """Guarantee that every user-required persona participates."""

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
            skills = [
                skill_id
                for skill_id in entry.get("skills", [])
                if _supports_role(skills_by_id.get(skill_id), "challenger")
            ][:MAX_SKILLS_PER_MEMBER]

            if not skills:
                skills = [
                    _select_skill(
                        role="challenger",
                        skills_by_id=skills_by_id,
                        preferred_ids=[],
                    )
                ]

            challengers.append(
                MeetingMember(
                    persona=persona_id,
                    skills=skills,
                    focus=entry["description"],
                    strictness=_default_strictness(
                        skill_ids=skills,
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
    """Append a required skill to a compatible member with capacity."""

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
    """Create a compatible member for one unassigned required skill."""

    associated_personas = [
        persona_id
        for persona_id, entry in personas_by_id.items()
        if skill_id in entry.get("skills", [])
        and _supports_role(entry, role)
    ]
    persona_id = _select_persona(
        role=role,
        personas_by_id=personas_by_id,
        preferred_ids=associated_personas,
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


def ensure_required_skills(
    *,
    participants: list[MeetingMember],
    challengers: list[MeetingMember],
    required_skills: list[str],
    personas_by_id: dict[str, dict[str, Any]],
    skills_by_id: dict[str, dict[str, Any]],
) -> tuple[list[MeetingMember], list[MeetingMember]]:
    """Guarantee that every required skill is assigned."""

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
