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

from pathlib import Path

from .llm_service.prompts import render_prompt

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
        file_prompt = render_prompt(
            "snapshot_file.md",
            file_path=file["path"],
            file_content=file["content"]
        )
        blocks.append(file_prompt)

    formatted_files = "\n\n".join(blocks)

    repository_prompt = render_prompt(
        "snapshot_repository.md",
        snapshot_tree=snapshot["tree"],
        formatted_files=formatted_files
    )

    return repository_prompt


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

        changes_prompt = render_prompt(
            "snapshot_changes.md",
            file_path=file_path,
            file_content=content
        )

        blocks.append(changes_prompt)

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
    init_prompt = render_prompt(
        "generator_input.md",
        repo_context=repo_context,
        user_prompt=user_prompt
    )
    return init_prompt


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
    retry_prompt = render_prompt(
        "generator_retry.md",
        repo_context=repo_context,
        user_prompt=user_prompt,
        previous_generator_output=previous_generator_output,
        reviewer_feedback=reviewer_feedback
    )
    return retry_prompt


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
    input_prompt = render_prompt(
        "reviewer_input.md",
        user_prompt=user_prompt,
        final_diff=final_diff,
        changed_file_contents=changed_file_contents
    )
    return input_prompt
