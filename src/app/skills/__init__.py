"""
Skill loader.

Skills are stored as Markdown documents with YAML front matter under
the skills/ directory.

The loader searches recursively so skills can be organised by category,
for example:

skills/
    code_review/
    security/
    seo/
    accessibility/

Skill names must be globally unique regardless of directory.
"""

from pathlib import Path

SKILLS_DIR = Path(__file__).parent

# TODO:
# Cache loaded skills in memory.
# Skills are immutable during one process lifetime and are currently
# read from disk on every reviewer invocation.
def load_skill(skill_name: str) -> str:
    """
    Load a skill by its logical name.

    The search is recursive under the skills directory.

    Raises:
        ValueError:
            - if the skill does not exist.
            - if multiple skills with the same name exist.

    Returns:
        The complete Markdown document, including YAML front matter.
    """
    matches = list(SKILLS_DIR.rglob(f"{skill_name}.md"))

    if not matches:
        raise ValueError(f"Unknown skill: {skill_name}")

    if len(matches) > 1:
        locations = "\n".join(str(path.relative_to(SKILLS_DIR)) for path in matches)
        raise ValueError(
            f"Multiple skills named '{skill_name}' found:\n{locations}"
        )

    return matches[0].read_text(encoding="utf-8")
