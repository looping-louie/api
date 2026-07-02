import json
from pathlib import Path
from typing import Any


VALID_STATUSES = {"pending", "done"}


def load_tasks(tasks_path: str) -> list[dict[str, Any]]:
    path = Path(tasks_path)

    if not path.exists():
        raise RuntimeError(f"Tasks file does not exist: {tasks_path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise RuntimeError("tasks.json must be a JSON array")

    for task in data:
        validate_task(task)

    return data


def save_tasks(tasks_path: str, tasks: list[dict[str, Any]]) -> None:
    path = Path(tasks_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_next_pending_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    for task in tasks:
        if task["status"] == "pending":
            return task
    return None


def mark_task_done(
    tasks: list[dict[str, Any]],
    task_id: str,
    run_id: str,
) -> None:
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "done"
            task["run_id"] = run_id
            return

    raise RuntimeError(f"Task not found: {task_id}")


def validate_task(task: dict[str, Any]) -> None:
    required = {"id", "status", "prompt", "run_id", "commit_message"}
    missing = required - set(task.keys())

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