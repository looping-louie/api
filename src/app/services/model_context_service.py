"""
Model file-change service.

Converts untrusted generator output into validated filesystem mutations.

Generator models never modify repositories directly. They return a structured
JSON document describing file operations such as create, replace and delete.

Responsibilities include:

- extracting structured JSON from model responses;
- validating the file-operation schema;
- rejecting unsupported operations and protected paths;
- preventing path traversal outside the execution workspace;
- applying validated changes to the temporary worktree.

This service forms the security boundary between arbitrary model output and
the local filesystem. It does not execute Git commands or apply changes to the
original user repository.
"""

import json
from pathlib import Path


# TODO:
# Consider supporting additional operations such as:
# - rename
# - move
# - mkdir
# if they prove beneficial without making prompts significantly harder.
ALLOWED_OPERATIONS = {"create", "replace", "delete"}

PROTECTED_PATH_PARTS = {
    ".git",
    ".looping-louie",
}


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

    if not isinstance(data, dict):
        raise ValueError("Generator JSON must be an object")

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


# TODO:
# Execute operations atomically.
# If one operation fails, previously applied operations should be rolled
# back instead of leaving the worktree partially modified.
def apply_file_operations(
    repo_path: str,
    operations: list[dict],
) -> None:
    """
    Apply validated file operations to a repository.

    Operations are validated again at the filesystem boundary and then
    executed sequentially inside the current worktree.

    The original repository is never modified directly.
    """
    root = Path(repo_path).resolve()

    for operation in operations:
        _validate_operation(operation)

        op = operation["operation"]
        relative_path = operation["path"]
        target = _safe_path(root, relative_path)

        if op == "create":
            if target.exists():
                raise ValueError(
                    f"Cannot create existing file: {relative_path}"
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                operation["content"],
                encoding="utf-8",
            )

        elif op == "replace":
            if not target.exists():
                raise ValueError(
                    f"Cannot replace missing file: {relative_path}"
                )

            if not target.is_file():
                raise ValueError(
                    f"Cannot replace non-file path: {relative_path}"
                )

            target.write_text(
                operation["content"],
                encoding="utf-8",
            )

        elif op == "delete":
            if not target.exists():
                raise ValueError(
                    f"Cannot delete missing file: {relative_path}"
                )

            if target.is_dir():
                raise ValueError(
                    f"Cannot delete directory: {relative_path}"
                )

            target.unlink()


def _validate_operation(operation: dict) -> None:
    """
    Validate one file operation.

    Ensures the requested operation follows the supported schema and does not
    target protected repository paths before any filesystem access occurs.
    """
    if not isinstance(operation, dict):
        raise ValueError("Each operation must be an object")

    op = operation.get("operation")
    path = operation.get("path")

    if op not in ALLOWED_OPERATIONS:
        raise ValueError(f"Invalid operation: {op}")

    if not path or not isinstance(path, str):
        raise ValueError("Operation path must be a non-empty string")

    operation_path = Path(path)

    if operation_path.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {path}")

    path_parts = operation_path.parts

    if ".." in path_parts:
        raise ValueError(
            f"Parent path traversal is not allowed: {path}"
        )

    if any(part in PROTECTED_PATH_PARTS for part in path_parts):
        raise ValueError(
            f"Protected path cannot be modified: {path}"
        )

    if op in {"create", "replace"}:
        content = operation.get("content")

        if not isinstance(content, str):
            raise ValueError(
                f"{op} operation requires string content"
            )

    if op == "delete" and "content" in operation:
        raise ValueError(
            "delete operation must not include content"
        )


def _safe_path(root: Path, relative_path: str) -> Path:
    """
    Resolve a repository-relative path and ensure it remains inside the root.
    """
    target = (root / relative_path).resolve()

    if not target.is_relative_to(root):
        raise ValueError(
            f"Path escapes repository: {relative_path}"
        )

    return target