from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills"


def load_skill(skill_name: str) -> str:
    path = SKILLS_DIR / f"{skill_name}.md"

    if not path.exists():
        raise ValueError(f"Unknown skill: {skill_name}")

    return path.read_text(encoding="utf-8")