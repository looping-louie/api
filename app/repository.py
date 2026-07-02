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
    s = str(path)

    for i, prefix in enumerate(PRIORITY_PATHS):
        if s.startswith(prefix) or s == prefix:
            return (0, i, s)

    return (1, 999, s)

MAX_FILE_CHARS = 20_000
MAX_TOTAL_CHARS = 80_000


def build_snapshot(repo_path: str) -> dict:
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