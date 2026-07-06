"""
Select the minimum useful reviewer set for one task.
"""
from typing import Any
from src.app.schemas import ReviewerAssignment, SkillPlan
from src.app.services.llm_service.openai import plan_skills_with_openai
from src.app.skills import load_skill_registry


MAX_SELECTED_REVIEWERS = 3


async def create_skill_plan(
    *,
    model: str,
    task_prompt: str,
    project_profile: dict[str, Any],
    constitution: str,
    required_skills: list[str],
) -> SkillPlan:
    """
    Ask the planner for a minimal task-specific reviewer configuration.
    """
    registry = load_skill_registry()
    registry_by_id = {
        entry["id"]: entry
        for entry in registry
    }

    unknown_required = set(required_skills) - registry_by_id.keys()

    if unknown_required:
        raise ValueError(
            "Required skills are not present in registry.json: "
            f"{sorted(unknown_required)}"
        )

    raw_plan = await plan_skills_with_openai(
        model=model,
        task_prompt=task_prompt,
        project_profile=project_profile,
        constitution=constitution,
        registry=registry,
        required_skills=required_skills,
        max_reviewers=MAX_SELECTED_REVIEWERS,
    )

    return _normalise_skill_plan(
        raw_plan=raw_plan,
        registry_by_id=registry_by_id,
        required_skills=required_skills,
    )


def _normalise_skill_plan(
    *,
    raw_plan: dict[str, Any],
    registry_by_id: dict[str, dict[str, Any]],
    required_skills: list[str],
) -> SkillPlan:
    """
    Validate planner choices and fill strictness defaults locally.
    """
    phase = raw_plan.get("phase")

    if phase not in {"prototype", "mvp", "production"}:
        phase = "prototype"

    reasoning = raw_plan.get("reasoning")

    if not isinstance(reasoning, str) or not reasoning.strip():
        reasoning = "Planner did not provide reasoning."

    raw_reviewers = raw_plan.get("reviewers", [])

    if not isinstance(raw_reviewers, list):
        raw_reviewers = []

    selected: dict[str, ReviewerAssignment] = {}

    for item in raw_reviewers:
        if not isinstance(item, dict):
            continue

        skill_id = item.get("skill")

        if skill_id not in registry_by_id:
            continue

        registry_entry = registry_by_id[skill_id]
        default = registry_entry["default_strictness"][phase]

        strictness = item.get("strictness", default)

        if not isinstance(strictness, int):
            strictness = default

        # Prevent arbitrary extreme deviations from registry defaults.
        strictness = max(default - 15, min(default + 15, strictness))
        strictness = max(0, min(100, strictness))

        focus = item.get("focus")

        if not isinstance(focus, str) or not focus.strip():
            focus = registry_entry["description"]

        selected[skill_id] = ReviewerAssignment(
            skill=skill_id,
            strictness=strictness,
            focus=focus.strip(),
        )

    for skill_id in required_skills:
        if skill_id in selected:
            continue

        entry = registry_by_id[skill_id]

        selected[skill_id] = ReviewerAssignment(
            skill=skill_id,
            strictness=entry["default_strictness"][phase],
            focus=entry["description"],
        )

    reviewers = list(selected.values())[:MAX_SELECTED_REVIEWERS]

    if not reviewers:
        raise RuntimeError(
            "Skill planner did not select any valid reviewer"
        )

    return SkillPlan(
        phase=phase,
        reasoning=reasoning.strip(),
        reviewers=reviewers,
    )
