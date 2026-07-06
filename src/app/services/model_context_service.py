"""
Model context construction service.

Builds the repository context and prompt payloads sent to generator and
reviewer models.

Responsibilities include:

- scanning the execution worktree;
- filtering irrelevant, generated or unsupported files;
- prioritising source paths within a bounded context budget;
- reading the full contents of files changed during an iteration;
- formatting repository snapshots for model consumption;
- constructing initial, retry and reviewer prompts.

This service controls what repository information is exposed to models and how
that information is represented. It does not invoke models, mutate files or
execute Git commands.
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

IGNORED_DIRS = {
    ".git",
    ".looping-louie",
    "__pycache__",
    "env",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
}

IGNORED_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    ".DS_Store",
}

INCLUDED_EXTENSIONS = {
    ".html",
    ".css",
    ".js",
    ".ts",
    ".vue",
    ".py",
    ".md",
    ".json",
    ".txt",
    ".toml",
    ".yml",
    ".yaml",
}

PRIORITY_PATHS = (
    "app.vue",
    "layouts/",
    "pages/",
    "components/",
    "composables/",
    "plugins/",
    "nuxt.config.ts",
    "package.json",
)

MAX_FILE_CHARS = 20_000
MAX_TOTAL_CHARS = 80_000


def _snapshot_priority(relative_path: Path) -> tuple[int, int, str]:
    """
    Sort repository paths so the most relevant source files appear first.

    The path must be relative to the repository root because priority prefixes
    such as `pages/` and `components/` are repository-relative.

    Prioritisation matters because snapshots have a global character budget.
    """
    path_string = relative_path.as_posix()

    for index, prefix in enumerate(PRIORITY_PATHS):
        if path_string == prefix or path_string.startswith(prefix):
            return 0, index, path_string

    return 1, len(PRIORITY_PATHS), path_string


# TODO:
# Replace the global snapshot with task-aware context selection.
# The current strategy sends a broad repository snapshot; future versions
# should select files based on the task, changed paths and references.
def build_snapshot(repo_path: str | Path) -> dict:
    """
    Build a bounded text snapshot of a repository.

    Ignored directories, protected paths, symbolic links and unsupported files
    are skipped. Large files and the total included file content are capped.

    Args:
        repo_path:
            Repository or worktree whose context should be collected.

    Returns:
        A dictionary containing:

        - root: absolute repository path;
        - tree: newline-separated repository tree;
        - files: selected text files and their contents.
    """
    root = Path(repo_path).expanduser().resolve()

    if not root.exists():
        raise RuntimeError(f"Repository does not exist: {root}")

    if not root.is_dir():
        raise RuntimeError(f"Repository path is not a directory: {root}")

    tree_lines: list[str] = []
    files: list[dict[str, str]] = []
    total_chars = 0

    paths = sorted(
        root.rglob("*"),
        key=lambda path: _snapshot_priority(path.relative_to(root)),
    )

    for path in paths:
        relative = path.relative_to(root)

        if any(part in IGNORED_DIRS for part in relative.parts):
            continue

        if path.name in IGNORED_FILES:
            continue

        # Do not follow links that could expose content outside the repository.
        if path.is_symlink():
            continue

        relative_string = relative.as_posix()

        if path.is_dir():
            tree_lines.append(f"{relative_string}/")
            continue

        if not path.is_file():
            continue

        tree_lines.append(relative_string)

        if path.suffix.lower() not in INCLUDED_EXTENSIONS:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n\n[TRUNCATED]"

        if total_chars + len(content) > MAX_TOTAL_CHARS:
            continue

        files.append(
            {
                "path": relative_string,
                "content": content,
            }
        )
        total_chars += len(content)

    return {
        "root": str(root),
        "tree": "\n".join(tree_lines),
        "files": files,
    }


def format_snapshot_for_prompt(snapshot: dict) -> str:
    """
    Convert a repository snapshot into prompt-ready text.

    Args:
        snapshot:
            Snapshot returned by `build_snapshot`.

    Returns:
        Repository tree and selected file contents formatted for a model.
    """
    blocks = []

    for file in snapshot["files"]:
        blocks.append(
            f"""--- FILE: {file["path"]} ---
{file["content"]}
--- END FILE ---"""
        )

    formatted_files = "\n\n".join(blocks)

    return f"""
Repository tree:

{snapshot["tree"]}

Repository files:

{formatted_files}
""".strip()


def read_changed_file_contents(
    repo_path: str | Path,
    changed_files: list[str],
) -> str:
    """
    Read the full contents of files changed during the current iteration.

    Reviewers receive both the Git diff and the resulting file contents so they
    can assess changed lines in their complete context.

    Deleted files and unsupported binary files are omitted.

    Args:
        repo_path:
            Repository or worktree containing the candidate changes.

        changed_files:
            Repository-relative paths reported by Git.

    Returns:
        Prompt-ready blocks containing the changed file contents.
    """
    root = Path(repo_path).expanduser().resolve()
    blocks: list[str] = []

    for file_path in changed_files:
        path = (root / file_path).resolve()

        if not path.is_relative_to(root):
            raise ValueError(f"Changed file escapes repository: {file_path}")

        if any(part in IGNORED_DIRS for part in Path(file_path).parts):
            continue

        if path.is_symlink():
            continue

        # Deleted files are represented by the Git diff and have no resulting
        # contents to include.
        if not path.exists() or not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        blocks.append(
            f"""--- CHANGED FILE: {file_path} ---
{content}
--- END CHANGED FILE ---"""
        )

    return "\n\n".join(blocks)


# TODO:
# Split prompts into stable and dynamic sections so providers supporting
# prompt caching can reuse the repository context across iterations.
def build_initial_generator_prompt(
    repo_context: str,
    user_prompt: str,
) -> str:
    """
    Build the generator prompt for the first iteration.

    The provider-level system prompt defines the required output format. This
    prompt supplies the repository context and the requested development task.
    """
    return f"""
Repository context:

{repo_context}

User task:

{user_prompt}
""".strip()


def build_retry_generator_prompt(
    repo_context: str,
    user_prompt: str,
    previous_generator_output: str,
    reviewer_feedback: str,
) -> str:
    """
    Build the generator prompt for a retry iteration.

    Includes the original repository context, the requested task, the previous
    generator response and the feedback that caused the iteration to fail.
    """
    return f"""
Repository context:

{repo_context}

User task:

{user_prompt}

Previous generator output:

{previous_generator_output}

Reviewer or system feedback:

{reviewer_feedback}

Produce a corrected solution that addresses all feedback.
""".strip()


# TODO:
# Support multimodal reviewer inputs such as screenshots, diagrams and other
# execution artefacts.
def build_reviewer_input(
    user_prompt: str,
    final_diff: str,
    changed_file_contents: str,
) -> str:
    """
    Build the candidate-change context sent to reviewer models.

    Reviewers receive the original task, the Git diff and the full contents of
    every changed file.

    Args:
        user_prompt:
            Original development task.

        final_diff:
            Git diff generated from the worktree changes.

        changed_file_contents:
            Full resulting contents of the changed files.

    Returns:
        Complete reviewer input.
    """
    return f"""
Original user prompt:

{user_prompt}

Git diff:

{final_diff}

Changed files:

{changed_file_contents}
""".strip()


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

