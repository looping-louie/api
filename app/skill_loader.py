from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills"


def load_skill(skill_name: str) -> str:
    matches = list(SKILLS_DIR.rglob(f"{skill_name}.md"))

    if not matches:
        raise ValueError(f"Unknown skill: {skill_name}")

    if len(matches) > 1:
        locations = "\n".join(str(path.relative_to(SKILLS_DIR)) for path in matches)
        raise ValueError(
            f"Multiple skills named '{skill_name}' found:\n{locations}"
        )

    return matches[0].read_text(encoding="utf-8")