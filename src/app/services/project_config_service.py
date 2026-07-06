from pathlib import Path


DEFAULT_CONSTITUTION = """
Implement only the requested task.
Avoid unrelated changes.
Preserve existing behaviour unless explicitly requested.
Blocking issues must describe concrete defects rather than preferences.
Never expose secrets or introduce clear security vulnerabilities.
""".strip()


def load_constitution(repo_path: str) -> str:
    path = (
        Path(repo_path).expanduser().resolve()
        / ".looping-louie"
        / "constitution.md"
    )

    if not path.exists():
        return DEFAULT_CONSTITUTION

    return path.read_text(encoding="utf-8").strip()