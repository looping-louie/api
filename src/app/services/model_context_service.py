"""
Repository context builder.

Builds the repository snapshot that is sent to the generator model.

The snapshot contains:
- a filtered repository tree
- selected text files
- prioritised source files

The goal is to give the model enough context to make safe changes without
sending irrelevant or huge files such as lockfiles, build output or dependencies.
"""

from pathlib import Path

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

def _snapshot_priority(path: Path):
    """
    Sort repository paths so the most relevant source files are included first.

    This matters because the snapshot has a global character budget.
    """
    s = str(path)

    for i, prefix in enumerate(PRIORITY_PATHS):
        if s.startswith(prefix) or s == prefix:
            return (0, i, s)

    return (1, 999, s)

MAX_FILE_CHARS = 20_000
MAX_TOTAL_CHARS = 80_000

# TODO:
# Replace the global snapshot with task-aware context selection.
# The current strategy sends a broad repository snapshot; future versions
# should select files based on the task, changed paths and references.
def build_snapshot(repo_path: str) -> dict:
    """
    Build a bounded text snapshot of a repository.

    Ignored directories and files are skipped.
    Only supported text extensions are included.
    Large files and the total snapshot size are capped.
    """
    root = Path(repo_path).resolve()
    tree_lines = []
    files = []
    total_chars = 0

    paths = sorted(root.rglob("*"), key=_snapshot_priority)
    for path in paths:
        relative = path.relative_to(root)

        if any(part in IGNORED_DIRS for part in relative.parts):
            continue

        if path.name in IGNORED_FILES:
            continue

        if path.is_dir():
            tree_lines.append(f"{relative}/")
            continue

        tree_lines.append(str(relative))

        if path.suffix not in INCLUDED_EXTENSIONS:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n\n[TRUNCATED]"

        if total_chars + len(content) > MAX_TOTAL_CHARS:
            continue

        files.append({"path": str(relative), "content": content})
        total_chars += len(content)

    return {"root": str(root), "tree": "\n".join(tree_lines), "files": files}


def format_snapshot_for_prompt(snapshot: dict) -> str:
    """
    Convert a repository snapshot into prompt-ready text for the generator.
    """
    blocks = []
    for file in snapshot["files"]:
        blocks.append(
            f"""--- FILE: {file["path"]} ---
{file["content"]}
--- END FILE ---"""
        )

    return f"""
Repository tree:

{snapshot["tree"]}

Repository files:

{chr(10).join(blocks)}
""".strip()


def read_changed_file_contents(repo_path: str, changed_files: list[str]) -> str:
    """
    Read the full contents of files changed by the current iteration.

    Reviewers receive both the git diff and the full changed files so they can
    understand context around the modified lines.
    """
    root = Path(repo_path)
    blocks = []

    for file_path in changed_files:
        path = root / file_path
        if not path.exists() or not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
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

    The prompt contains the repository snapshot and the user's requested task.
    """
    return f"""
Repository context:

{repo_context}

User task:

{user_prompt}

Return ONLY JSON file operations.
Do not return a git patch.
""".strip()


def build_retry_generator_prompt(
    repo_context: str,
    user_prompt: str,
    previous_generator_output: str,
    reviewer_feedback: str,
) -> str:
    """
    Build the generator prompt for retry iterations.

    In addition to the repository snapshot and user task, retry prompts include
    the previous generator output and reviewer feedback so the model can refine
    its proposal.
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

Return corrected JSON file operations only.
""".strip()


# TODO:
# Support multimodal reviewer inputs (screenshots, diagrams and other
# artefacts) in addition to text-based diffs.
def build_reviewer_input(
    user_prompt: str,
    final_diff: str,
    changed_file_contents: str,
) -> str:
    """
    Build the reviewer input.

    Reviewers receive:
    - the original user request;
    - the git diff produced by the generator;
    - the full contents of every changed file.

    This allows skills to review both the change itself and its surrounding
    context.
    """
    return f"""
Original user prompt:

{user_prompt}

Git diff:

{final_diff}

Changed files:

{changed_file_contents}
""".strip()