"""Artifact contracts, normalisation, and deterministic meeting validation."""

import json
import re
from typing import Any


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


def get_artifact_contract(meeting_type: str) -> str:
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


def get_local_contract_issues(
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


def build_round_feedback(
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


def extract_disagreements(
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


def normalise_artifact(*, meeting_type: str, artifact: str) -> str:
    """Normalise an artifact when its output type has a canonical format."""
    if meeting_type == "plan_implementation":
        return _normalise_tasks_json(artifact)

    return artifact.strip()

