"""
Build a compact repository profile for the skill planner.
"""

from collections import Counter
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".looping-louie",
    "node_modules",
    ".nuxt",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
}

SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".vue",
    ".html",
    ".css",
    ".scss",
    ".md",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
}


def build_project_profile(repo_path: str) -> dict:
    """
    Return compact structural signals without exposing file contents.
    """
    root = Path(repo_path).expanduser().resolve()

    extension_counts: Counter[str] = Counter()
    top_level_entries: list[str] = []
    source_file_count = 0
    approximate_source_chars = 0

    for path in root.iterdir():
        if path.name not in IGNORED_DIRS:
            suffix = "/" if path.is_dir() else ""
            top_level_entries.append(f"{path.name}{suffix}")

    for path in root.rglob("*"):
        relative = path.relative_to(root)

        if any(part in IGNORED_DIRS for part in relative.parts):
            continue

        if not path.is_file():
            continue

        suffix = path.suffix.lower()

        if suffix not in SOURCE_EXTENSIONS:
            continue

        source_file_count += 1
        extension_counts[suffix or "[none]"] += 1

        try:
            approximate_source_chars += path.stat().st_size
        except OSError:
            pass

    markers = {
        "nuxt": (root / "nuxt.config.ts").exists()
        or (root / "nuxt.config.js").exists(),
        "package_json": (root / "package.json").exists(),
        "fastapi": _contains_dependency(root / "requirements.txt", "fastapi")
        or _contains_dependency(root / "pyproject.toml", "fastapi"),
        "docker": (root / "Dockerfile").exists()
        or (root / "docker-compose.yml").exists()
        or (root / "compose.yml").exists(),
        "tests": any(
            candidate.exists()
            for candidate in (
                root / "tests",
                root / "test",
                root / "__tests__",
            )
        ),
    }

    return {
        "source_file_count": source_file_count,
        "approximate_source_chars": approximate_source_chars,
        "extension_counts": dict(extension_counts),
        "top_level_entries": sorted(top_level_entries)[:80],
        "markers": markers,
    }


def _contains_dependency(path: Path, dependency: str) -> bool:
    if not path.exists() or not path.is_file():
        return False

    try:
        return dependency.lower() in path.read_text(
            encoding="utf-8"
        ).lower()
    except (OSError, UnicodeDecodeError):
        return False