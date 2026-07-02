import json
from pathlib import Path


ALLOWED_OPERATIONS = {"create", "replace", "delete"}


def parse_file_operations(raw: str) -> list[dict]:
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


def _extract_json_object(raw: str) -> str:
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


def apply_file_operations(repo_path: str, operations: list[dict]) -> None:
    root = Path(repo_path).resolve()

    for operation in operations:
        op = operation["operation"]
        target = _safe_path(root, operation["path"])

        if op == "create":
            if target.exists():
                raise ValueError(f"Cannot create existing file: {operation['path']}")

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(operation["content"], encoding="utf-8")

        elif op == "replace":
            if not target.exists():
                raise ValueError(f"Cannot replace missing file: {operation['path']}")

            target.write_text(operation["content"], encoding="utf-8")

        elif op == "delete":
            if not target.exists():
                raise ValueError(f"Cannot delete missing file: {operation['path']}")

            if target.is_dir():
                raise ValueError(f"Cannot delete directory: {operation['path']}")

            target.unlink()


def _validate_operation(operation: dict) -> None:
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

    if op == "delete" and "content" in operation:
        raise ValueError("delete operation must not include content")


def _safe_path(root: Path, relative_path: str) -> Path:
    target = (root / relative_path).resolve()

    if not str(target).startswith(str(root)):
        raise ValueError(f"Path escapes repository: {relative_path}")

    return target