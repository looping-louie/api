"""Contract tests for the shared instruction business taxonomy."""

from src.app.catalogs.library import LibraryCategory
from src.app.catalogs.personas.loader import load_persona_catalog
from src.app.catalogs.skills.loader import load_skill_catalog


def test_packaged_instructions_use_the_stable_business_taxonomy() -> None:
    """Every packaged skill and persona uses one of twelve categories."""

    skills = load_skill_catalog()
    personas = load_persona_catalog()

    assert len(LibraryCategory) == 12
    assert all(
        isinstance(entry.category, LibraryCategory)
        for entry in (*skills, *personas)
    )
