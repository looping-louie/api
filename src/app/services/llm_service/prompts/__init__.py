"""Load and render model prompts from Markdown templates."""

from pathlib import Path
from string import Template


_PROMPTS_DIR = Path(__file__).parent


def render_prompt(filename: str, **variables: object) -> str:
    """Load and render a Markdown prompt template."""
    content = (_PROMPTS_DIR / filename).read_text(encoding="utf-8")
    normalized = {
        key: str(value)
        for key, value in variables.items()
    }

    return Template(content).substitute(normalized).strip()