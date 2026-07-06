"""
Task plan service.

Loads, validates, updates and persists the ordered development plan executed
by the harness.

Each task represents one logical repository change and is processed
sequentially. Successfully reviewed tasks are associated with the harness run
that produced them and marked as completed.

Responsibilities include:

- loading task plans from persistent storage;
- validating task definitions and status transitions;
- selecting the next pending task;
- recording successful task completion;
- persisting the updated execution plan deterministically.

The current implementation uses a JSON file as storage, while exposing
task-plan behaviour independently from the orchestration layer.
"""


import json
from pathlib import Path
from typing import Any


# TODO:
# Extend the task schema with optional execution settings such as:
# - max_iterations
# - skills
# - generator_model
# - reviewer_model
# allowing each task to override the defaults.
VALID_STATUSES = {"pending", "done"}


def load_tasks(tasks_path: str) -> list[dict[str, Any]]:
    """
    Load and validate a tasks.json file.

    Returns the complete list of tasks preserving their original order.
    """
    path = Path(tasks_path)

    if not path.exists():
        raise RuntimeError(f"Tasks file does not exist: {tasks_path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise RuntimeError("tasks.json must be a JSON array")

    # Detecta IDs duplicados.
    task_ids = [task["id"] for task in data]
    if len(task_ids) != len(set(task_ids)):
        raise RuntimeError("tasks.json contains duplicate task ids")

    for task in data:
        validate_task(task)

    return data


def save_tasks(tasks_path: str, tasks: list[dict[str, Any]]) -> None:
    """
    Persist the current task list to disk.

    Formatting is kept deterministic to minimise diffs while the file is
    being updated during execution.
    """
    path = Path(tasks_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_next_pending_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Return the first pending task.

    Tasks are always executed sequentially in file order.
    """
    for task in tasks:
        if task["status"] == "pending":
            return task
    return None


def mark_task_done(
    tasks: list[dict[str, Any]],
    task_id: str,
    run_id: str,
) -> None:
    """
    Mark a task as completed and record the harness run that produced it.
    """
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "done"
            task["run_id"] = run_id
            return

    raise RuntimeError(f"Task not found: {task_id}")


# TODO:
# Replace manual validation with a dedicated Pydantic Task model so
# task parsing is consistent with the rest of the API.
def validate_task(task: dict[str, Any]) -> None:
    """
    Validate one task definition.

    Raises RuntimeError if the task does not satisfy the expected schema.
    """
    required = {"id", "status", "prompt", "run_id", "commit_message"}
    missing = required - set(task.keys())
    run_id = task["run_id"]

    if missing:
        raise RuntimeError(f"Task is missing fields: {', '.join(sorted(missing))}")

    if task["status"] not in VALID_STATUSES:
        raise RuntimeError(f"Invalid task status: {task['status']}")

    if not isinstance(task["id"], str) or not task["id"]:
        raise RuntimeError("Task id must be a non-empty string")

    if not isinstance(task["prompt"], str) or not task["prompt"]:
        raise RuntimeError(f"Task {task['id']} prompt must be non-empty")

    if not isinstance(task["commit_message"], str) or not task["commit_message"]:
        raise RuntimeError(f"Task {task['id']} commit_message must be non-empty")

    if run_id is not None and not isinstance(run_id, str):
        raise RuntimeError(
            f"Task {task['id']} run_id must be a string or null"
        )

    if task["status"] == "done" and not run_id:
        raise RuntimeError(
            f"Completed task {task['id']} must contain a run_id"
        )
