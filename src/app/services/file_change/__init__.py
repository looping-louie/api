"""
File operation parser and executor.

Generator models do not modify repositories directly. Instead they return
a JSON document describing a sequence of file operations.

This module is responsible for:

- parsing generator output;
- validating every requested operation;
- protecting against invalid or unsafe paths;
- applying the operations inside the current worktree.

Only validated operations are allowed to reach the filesystem.
"""

import json
from pathlib import Path


# TODO:
# Consider supporting additional operations such as:
# - rename
# - move
# - mkdir
# if they prove beneficial without making prompts significantly harder.
ALLOWED_OPERATIONS = {"create", "replace", "replace_text", "delete"}


def parse_file_operations(raw: str) -> list[dict]:
    """
    Parse and validate generator output.

    The generator may wrap the JSON in Markdown fences or include additional
    text. This function extracts the JSON object, validates its schema and
    returns the list of file operations.
    """
    cleaned = _extract_json_object(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from generator: {exc}") from exc

    operations = data.get("operations")

    if not isinstance(operations, list):
        raise ValueError("Generator JSON must contain an operations list")

    for operation in operations:
        _validate_operation(operation)

    return operations

# TODO:
# Replace the current heuristic with a proper JSON extractor capable of
# recovering the first valid JSON object from arbitrary model output.
def _extract_json_object(raw: str) -> str:
    """
    Extract the first JSON object from a generator response.

    This provides a small amount of robustness against models that ignore the
    requested output format by wrapping the JSON in Markdown fences or adding
    extra text.
    """
    text = raw.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("Generator output does not contain a JSON object")

    return text[start : end + 1]


def _read_pending_content(
    *,
    target: Path,
    pending: dict[Path, str | None],
) -> str | None:
    """
    Return the latest simulated content for one path.

    Pending changes take precedence over the current filesystem state.
    """
    if target in pending:
        return pending[target]

    if not target.exists():
        return None

    if not target.is_file():
        raise ValueError(f"Path is not a file: {target}")

    return target.read_text(encoding="utf-8")


def _commit_pending_changes(
    pending: dict[Path, str | None],
) -> None:
    """
    Persist validated simulated changes to the filesystem.
    """
    for target, content in pending.items():
        if content is None:
            target.unlink()
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


# TODO:
# Execute operations atomically.
# If one operation fails, previously applied operations should be rolled
# back instead of leaving the worktree partially modified.
def apply_file_operations(
    repo_path: str,
    operations: list[dict],
) -> None:
    """
    Validate and apply file operations atomically.

    All operations are simulated in memory in their declared order. Filesystem
    writes occur only after every operation has succeeded.
    """
    root = Path(repo_path).resolve()
    pending: dict[Path, str | None] = {}

    for operation in operations:
        _validate_operation(operation)

        op = operation["operation"]
        relative_path = operation["path"]
        target = _safe_path(root, relative_path)

        current_content = _read_pending_content(
            target=target,
            pending=pending,
        )

        if op == "create":
            if current_content is not None:
                raise ValueError(
                    f"Cannot create existing file: {relative_path}"
                )

            pending[target] = operation["content"]

        elif op == "replace":
            if current_content is None:
                raise ValueError(
                    f"Cannot replace missing file: {relative_path}"
                )

            pending[target] = operation["content"]

        elif op == "replace_text":
            if current_content is None:
                raise ValueError(
                    f"Cannot modify missing file: {relative_path}"
                )

            old_content = operation["old_content"]
            matches = current_content.count(old_content)

            if matches == 0:
                raise ValueError(
                    "replace_text old_content was not found in "
                    f"{relative_path}"
                )

            if matches > 1:
                raise ValueError(
                    "replace_text old_content appears more than once in "
                    f"{relative_path}"
                )

            pending[target] = current_content.replace(
                old_content,
                operation["new_content"],
                1,
            )

        elif op == "delete":
            if current_content is None:
                raise ValueError(
                    f"Cannot delete missing file: {relative_path}"
                )

            pending[target] = None

    _commit_pending_changes(pending)



def _validate_operation(operation: dict) -> None:
    """
    Validate one file operation.

    Ensures the requested operation follows the supported schema before any
    filesystem access is attempted.
    """
    if not isinstance(operation, dict):
        raise ValueError("Each operation must be an object")

    op = operation.get("operation")
    path = operation.get("path")

    if op not in ALLOWED_OPERATIONS:
        raise ValueError(f"Invalid operation: {op}")

    if not path or not isinstance(path, str):
        raise ValueError("Operation path must be a non-empty string")

    if path.startswith("/"):
        raise ValueError(f"Absolute paths are not allowed: {path}")

    if ".." in Path(path).parts:
        raise ValueError(f"Parent path traversal is not allowed: {path}")

    if op in {"create", "replace"}:
        content = operation.get("content")
        if not isinstance(content, str):
            raise ValueError(f"{op} operation requires string content")

    if op == "delete" and any(
        key in operation
        for key in ("content", "old_content", "new_content")
    ):
        raise ValueError(
            "delete operation must not include file content"
        )

    if op == "replace_text":
        old_content = operation.get("old_content")
        new_content = operation.get("new_content")

        if not isinstance(old_content, str) or not old_content:
            raise ValueError(
                "replace_text operation requires non-empty old_content"
            )

        if not isinstance(new_content, str):
            raise ValueError(
                "replace_text operation requires string new_content"
            )

        if "content" in operation:
            raise ValueError(
                "replace_text operation must not include content"
            )


def _safe_path(root: Path, relative_path: str) -> Path:
    """
    Resolve a repository-relative path safely.

    Prevents path traversal attacks by ensuring the resolved path remains
    inside the repository root.
    """
    target = (root / relative_path).resolve()

    if not str(target).startswith(str(root)):
        raise ValueError(f"Path escapes repository: {relative_path}")

    return target